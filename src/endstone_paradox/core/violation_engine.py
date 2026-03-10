# violation_engine.py - Central violation processing, enforcement ladder,
# rate-limited alerts, evidence persistence, and cross-module correlation.

import time
import threading
from collections import defaultdict, deque
from enum import IntEnum
from typing import Optional, Dict, Any, List


class Severity(IntEnum):
    INFO = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    CRITICAL = 5


class EnforcementMode:
    LOGONLY = "logonly"
    SOFT = "soft"       # cancel + setback + notify  (default)
    HARD = "hard"       # faster escalation, shorter ladder


# Enforcement actions in escalation order
ACTION_WARN = "warn"
ACTION_CANCEL = "cancel"
ACTION_SETBACK = "setback"
ACTION_KICK = "kick"
ACTION_BAN = "ban"


class ViolationEntry:
    __slots__ = ("module", "severity", "evidence", "timestamp", "action_hint")

    def __init__(self, module: str, severity: int, evidence: dict,
                 action_hint: Optional[str] = None):
        self.module = module
        self.severity = severity
        self.evidence = evidence
        self.timestamp = time.time()
        self.action_hint = action_hint


class ViolationEngine:
    """Centralised violation processor with rolling buffers, enforcement ladder,
    rate-limited staff alerts, and write-behind evidence persistence."""

    # --- tunables ---
    DECAY_WINDOW = 600.0          # 10 min rolling window
    ALERT_COOLDOWN = 10.0         # per-player-per-module staff alert cooldown (s)
    FLUSH_INTERVAL = 30.0         # write-behind buffer flush interval (s)
    MAX_BUFFER_PER_PLAYER = 50    # max violations kept in memory per player

    # Escalation thresholds (cumulative score within decay window)
    SOFT_LADDER = {
        0:  ACTION_WARN,
        10: ACTION_CANCEL,
        30: ACTION_SETBACK,
        60: ACTION_KICK,
        120: ACTION_BAN,
    }
    HARD_LADDER = {
        0:  ACTION_CANCEL,
        10: ACTION_SETBACK,
        25: ACTION_KICK,
        50: ACTION_BAN,
    }

    def __init__(self, plugin):
        self.plugin = plugin
        self.db = plugin.db
        self.logger = plugin.logger

        # enforcement mode
        stored = self.db.get("config", "enforcement_mode")
        self._mode = stored if stored in (EnforcementMode.LOGONLY,
                                           EnforcementMode.SOFT,
                                           EnforcementMode.HARD) else EnforcementMode.SOFT

        # per-player rolling violation buffers: uuid -> deque[ViolationEntry]
        self._buffers: Dict[str, deque] = defaultdict(lambda: deque(maxlen=self.MAX_BUFFER_PER_PLAYER))

        # alert cooldowns: (uuid, module) -> last_alert_time
        self._alert_cooldowns: Dict[tuple, float] = {}

        # temporary exemptions: (uuid, module) -> expire_time
        self._exemptions: Dict[tuple, float] = {}

        # watchers: uuid_watcher -> {uuid_target, expire_time}
        self._watchers: Dict[str, dict] = {}

        # write-behind buffer (pending DB writes)
        self._pending_writes: List[dict] = []
        self._write_lock = threading.Lock()
        self._last_flush = time.time()

        # ensure violations table exists
        self.db._ensure_table("violations")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def mode(self) -> str:
        return self._mode

    def set_mode(self, mode: str):
        if mode in (EnforcementMode.LOGONLY, EnforcementMode.SOFT, EnforcementMode.HARD):
            self._mode = mode
            self.db.set("config", "enforcement_mode", mode)

    def emit_violation(self, player, module: str, severity: int,
                       evidence: dict, action_hint: Optional[str] = None):
        """Primary entry point. Modules call this instead of punishing directly."""
        if player is None:
            return

        uuid_str = str(player.unique_id) if hasattr(player, 'unique_id') else None
        if uuid_str is None:
            return

        # check exemptions
        now = time.time()
        if self._is_exempt(uuid_str, module, now):
            return

        entry = ViolationEntry(module, severity, evidence, action_hint)
        self._buffers[uuid_str].append(entry)

        # prune decayed entries
        self._prune(uuid_str, now)

        # calculate cumulative score
        score = self._calc_score(uuid_str, now)

        # determine enforcement action
        action = self._resolve_action(score, action_hint)

        # log evidence to write-behind buffer
        self._queue_evidence(uuid_str, player.name if hasattr(player, 'name') else "?",
                             module, severity, evidence, action, now)

        # rate-limited staff alert
        self._maybe_alert(uuid_str, player, module, severity, evidence, action, now)

        # stream to watchers
        self._notify_watchers(uuid_str, player, module, severity, evidence, action, now)

        # enforce (unless logonly)
        if self._mode != EnforcementMode.LOGONLY:
            self._enforce(player, action, module, evidence)

        # Push violation report to Global Ban API (for cross-server intelligence)
        if hasattr(self.plugin, '_global_api') and self.plugin._global_api:
            try:
                xuid = uuid_str if uuid_str else ""
                self.plugin._global_api.push_report(
                    player_name=player.name if hasattr(player, 'name') else "?",
                    module=module, severity=severity,
                    evidence=evidence, player_xuid=xuid
                )
            except Exception:
                pass

    def add_exemption(self, uuid_str: str, module: str, duration_s: float):
        """Temporarily exempt a player from a module (or 'all')."""
        self._exemptions[(uuid_str, module)] = time.time() + duration_s

    def remove_exemption(self, uuid_str: str, module: str):
        self._exemptions.pop((uuid_str, module), None)

    def add_watcher(self, watcher_uuid: str, target_uuid: str, duration_s: float):
        self._watchers[watcher_uuid] = {
            "target": target_uuid,
            "expire": time.time() + duration_s,
        }

    def remove_watcher(self, watcher_uuid: str):
        self._watchers.pop(watcher_uuid, None)

    def get_recent(self, uuid_str: str, n: int = 5) -> List[dict]:
        """Return last N violation entries from DB for a player."""
        data = self.db.get("violations", uuid_str, [])
        if not isinstance(data, list):
            return []
        return data[-n:]

    def on_player_leave(self, player):
        uuid_str = str(player.unique_id) if hasattr(player, 'unique_id') else None
        if uuid_str:
            self._buffers.pop(uuid_str, None)
            # clean expired exemptions
            now = time.time()
            to_remove = [k for k, v in self._exemptions.items()
                         if k[0] == uuid_str or v < now]
            for k in to_remove:
                self._exemptions.pop(k, None)

    def flush(self):
        """Write pending evidence entries to DB."""
        with self._write_lock:
            if not self._pending_writes:
                return
            batch = self._pending_writes[:]
            self._pending_writes.clear()

        # Group by UUID for efficient writes
        by_uuid: Dict[str, list] = defaultdict(list)
        for entry in batch:
            by_uuid[entry["uuid"]].append(entry)

        for uuid_str, entries in by_uuid.items():
            try:
                existing = self.db.get("violations", uuid_str, [])
                if not isinstance(existing, list):
                    existing = []
                existing.extend(entries)
                # Keep only last 100 entries per player
                if len(existing) > 100:
                    existing = existing[-100:]
                self.db.set("violations", uuid_str, existing)
            except Exception as e:
                self.logger.error(f"[ViolationEngine] flush error: {e}")

        self._last_flush = time.time()

    def maybe_flush(self):
        """Called periodically — flushes if interval elapsed."""
        if time.time() - self._last_flush >= self.FLUSH_INTERVAL:
            self.flush()

    def clear_player(self, uuid_str: str):
        """Clear all violations and baselines for a player."""
        self._buffers.pop(uuid_str, None)
        try:
            self.db.delete("violations", uuid_str)
        except Exception:
            pass
        try:
            self.db.delete("baselines", uuid_str)
        except Exception:
            pass
        # Reset baseline in memory
        baseline = getattr(self.plugin, 'player_baseline', None)
        if baseline:
            baseline._profiles.pop(uuid_str, None)
            baseline._dirty.discard(uuid_str)

    def clear_all(self):
        """Clear all violations and baselines for all players."""
        self._buffers.clear()
        try:
            for item in self.db.get_all("violations"):
                if isinstance(item, (list, tuple)) and len(item) == 2:
                    self.db.delete("violations", item[0])
                elif isinstance(item, dict) and "key" in item:
                    self.db.delete("violations", item["key"])
        except Exception:
            pass
        try:
            for item in self.db.get_all("baselines"):
                if isinstance(item, (list, tuple)) and len(item) == 2:
                    self.db.delete("baselines", item[0])
                elif isinstance(item, dict) and "key" in item:
                    self.db.delete("baselines", item["key"])
        except Exception:
            pass
        baseline = getattr(self.plugin, 'player_baseline', None)
        if baseline:
            baseline._profiles.clear()
            baseline._dirty.clear()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _is_exempt(self, uuid_str: str, module: str, now: float) -> bool:
        # Check specific module exemption
        key = (uuid_str, module)
        if key in self._exemptions:
            if now < self._exemptions[key]:
                return True
            else:
                del self._exemptions[key]

        # Check "all" exemption
        key_all = (uuid_str, "all")
        if key_all in self._exemptions:
            if now < self._exemptions[key_all]:
                return True
            else:
                del self._exemptions[key_all]

        return False

    def _prune(self, uuid_str: str, now: float):
        buf = self._buffers.get(uuid_str)
        if not buf:
            return
        while buf and (now - buf[0].timestamp) > self.DECAY_WINDOW:
            buf.popleft()

    def _calc_score(self, uuid_str: str, now: float) -> float:
        """Sum severity scores with time decay weighting."""
        buf = self._buffers.get(uuid_str)
        if not buf:
            return 0.0
        total = 0.0
        for entry in buf:
            age = now - entry.timestamp
            # Linear decay: full weight at 0s, zero weight at DECAY_WINDOW
            weight = max(0.0, 1.0 - age / self.DECAY_WINDOW)
            total += entry.severity * weight
        return total

    def _resolve_action(self, score: float, action_hint: Optional[str]) -> str:
        ladder = self.HARD_LADDER if self._mode == EnforcementMode.HARD else self.SOFT_LADDER
        action = ACTION_WARN
        for threshold, act in sorted(ladder.items()):
            if score >= threshold:
                action = act
        # Honor action_hint if it's less severe (module says "just setback")
        if action_hint == ACTION_SETBACK and action in (ACTION_KICK, ACTION_BAN):
            # Module prefers setback — only override ban if score is really high
            if score < 60:
                action = ACTION_SETBACK
        return action

    def _enforce(self, player, action: str, module: str, evidence: dict):
        try:
            if action == ACTION_WARN:
                pass  # just alert (already handled)
            elif action == ACTION_CANCEL:
                pass  # caller already cancelled the event
            elif action == ACTION_SETBACK:
                # Teleport player to last safe position
                self._setback(player)
            elif action == ACTION_KICK:
                player.kick(f"§c[Paradox] Kicked for {module} violations")
            elif action == ACTION_BAN:
                uuid_str = str(player.unique_id)
                reason = f"Auto-ban: {module} violations"
                self.db.set("bans", uuid_str, {
                    "name": player.name,
                    "reason": reason,
                    "time": time.time(),
                })
                player.kick(f"§c[Paradox] Banned for {module} violations")

                # Push auto-ban to Global Ban API
                if hasattr(self.plugin, '_global_api') and self.plugin._global_api:
                    try:
                        self.plugin._global_api.push_ban(
                            player_name=player.name,
                            reason=reason,
                            player_xuid=uuid_str,
                            category="ban"
                        )
                    except Exception:
                        pass
        except Exception as e:
            self.logger.error(f"[ViolationEngine] enforce error: {e}")

    def _setback(self, player):
        """Teleport player back to last safe ground position."""
        try:
            uuid_str = str(player.unique_id)
            # Check if fly module has a landing position
            fly_mod = self.plugin.get_module("fly")
            if fly_mod and hasattr(fly_mod, '_player_data'):
                data = fly_mod._player_data.get(uuid_str, {})
                landing = data.get("landing")
                if landing:
                    player.teleport(landing)
                    return
            # Fallback: teleport down to nearest solid block
            loc = player.location
            player.teleport(loc)  # at minimum, stop their momentum
        except Exception:
            pass

    def _maybe_alert(self, uuid_str: str, player, module: str, severity: int,
                     evidence: dict, action: str, now: float):
        key = (uuid_str, module)
        last = self._alert_cooldowns.get(key, 0)
        if now - last < self.ALERT_COOLDOWN:
            return

        self._alert_cooldowns[key] = now

        name = player.name if hasattr(player, 'name') else "?"
        # Build concise alert
        ev_str = ", ".join(f"{k}={v}" for k, v in evidence.items()
                          if k not in ("module",))
        msg = (f"§2[§7Paradox§2]§e §c{name}§e {module} "
               f"[{Severity(severity).name}] ({ev_str}) → {action}")
        self.plugin.send_to_level4(msg)

    def _notify_watchers(self, uuid_str: str, player, module: str,
                         severity: int, evidence: dict, action: str, now: float):
        expired = []
        for w_uuid, info in self._watchers.items():
            if info["target"] != uuid_str:
                continue
            if now > info["expire"]:
                expired.append(w_uuid)
                continue
            # Find watcher player and send them the violation
            for online in self.plugin.server.online_players:
                if str(online.unique_id) == w_uuid:
                    name = player.name if hasattr(player, 'name') else "?"
                    ev_str = ", ".join(f"{k}={v}" for k, v in evidence.items())
                    online.send_message(
                        f"§2[§7Watch§2]§e §c{name}§e {module} "
                        f"[{Severity(severity).name}] ({ev_str}) → {action}"
                    )
                    break
        for w in expired:
            self._watchers.pop(w, None)

    def _queue_evidence(self, uuid_str: str, name: str, module: str,
                        severity: int, evidence: dict, action: str, now: float):
        entry = {
            "uuid": uuid_str,
            "name": name,
            "module": module,
            "severity": severity,
            "evidence": evidence,
            "action": action,
            "time": now,
        }
        with self._write_lock:
            self._pending_writes.append(entry)
