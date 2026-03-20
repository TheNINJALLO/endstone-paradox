# autoclicker.py - Multi-platform autoclicker detection with air-click tracking
# and click consistency analysis

import time
import statistics
from collections import deque, defaultdict
from endstone_paradox.modules.base import BaseModule


# Bedrock DeviceOS values (from login ClientData)
DEVICE_ANDROID = 1
DEVICE_IOS = 2
DEVICE_WINDOWS = 7      # Win10
DEVICE_XBOX = 11
DEVICE_PLAYSTATION = 12
DEVICE_SWITCH = 13

_MOBILE_DEVICES = {DEVICE_ANDROID, DEVICE_IOS}
_CONSOLE_DEVICES = {DEVICE_XBOX, DEVICE_PLAYSTATION, DEVICE_SWITCH}
_PC_DEVICES = {DEVICE_WINDOWS}  # also default fallback


class AutoClickerModule(BaseModule):
    """
    Enhanced autoclicker detection:
    1. Per-platform CPS thresholds (PC / Mobile / Console)
    2. Air-click tracking via PlayerAuthInputPacket (InputData flags)
    3. Click consistency (variance) analysis - bots click with inhuman regularity
    4. Sensitivity scaling (1-10)
    """

    name = "autoclicker"

    # --- Default CPS caps per platform ---
    # These are the BASE values at sensitivity 5; sensitivity scaling adjusts them.
    CPS_PC = 22          # butterfly / jitter clicking caps out ~20
    CPS_MOBILE = 16      # multi-finger tapping
    CPS_CONSOLE = 12     # controller trigger
    CPS_DEFAULT = 22     # fallback

    # Consistency: coefficient of variation threshold (stddev / mean).
    # Human clicks have high variance (CV > 0.15).  Bots are very regular (CV < 0.08).
    MIN_CV_THRESHOLD = 0.08    # Below this = suspiciously consistent

    WINDOW_SIZE = 1.0          # sliding window in seconds
    AIR_WINDOW = 1.0           # air-click sliding window

    # Minimum clicks in window before we run consistency analysis
    MIN_CLICKS_FOR_CV = 8

    def on_start(self):
        # Entity-hit tracking:  uuid -> deque of timestamps
        self._hit_data: dict[str, deque] = {}
        # Air-click tracking:   uuid -> deque of timestamps
        self._air_data: dict[str, deque] = {}
        # Player platform map:  uuid -> "pc" | "mobile" | "console"
        self._platform: dict[str, str] = {}
        # Consecutive flag counter for escalation
        self._flags: dict[str, int] = defaultdict(int)

        # Allow per-server override from DB
        for key, attr in [("cps_pc", "CPS_PC"), ("cps_mobile", "CPS_MOBILE"),
                          ("cps_console", "CPS_CONSOLE")]:
            custom = self.db.get("config", key)
            if custom is not None:
                setattr(self, attr, int(custom))

    def on_stop(self):
        self._hit_data.clear()
        self._air_data.clear()
        self._platform.clear()
        self._flags.clear()

    # ------------------------------------------------------------------
    # Platform detection on join
    # ------------------------------------------------------------------

    def on_player_join(self, player):
        """Detect player platform from device_os (set by Endstone from login)."""
        uuid_str = str(player.unique_id)
        device_os = getattr(player, "device_os", None) or getattr(player, "device_id", None)

        if device_os is not None:
            device_os = int(device_os) if not isinstance(device_os, int) else device_os
            if device_os in _MOBILE_DEVICES:
                self._platform[uuid_str] = "mobile"
            elif device_os in _CONSOLE_DEVICES:
                self._platform[uuid_str] = "console"
            else:
                self._platform[uuid_str] = "pc"
        else:
            self._platform[uuid_str] = "pc"  # default fallback

    def on_player_leave(self, player):
        uuid_str = str(player.unique_id)
        self._hit_data.pop(uuid_str, None)
        self._air_data.pop(uuid_str, None)
        self._platform.pop(uuid_str, None)
        self._flags.pop(uuid_str, None)

    # ------------------------------------------------------------------
    # CPS threshold for a given player (sensitivity-scaled)
    # ------------------------------------------------------------------

    def _get_max_cps(self, uuid_str: str) -> int:
        """Return the CPS cap for the player's platform, scaled by sensitivity."""
        platform = self._platform.get(uuid_str, "pc")
        if platform == "mobile":
            base = self.CPS_MOBILE
        elif platform == "console":
            base = self.CPS_CONSOLE
        else:
            base = self.CPS_PC

        # Sensitivity scaling: sens 1 = base * 1.5, sens 10 = base * 0.5
        # sens 5 = base * 1.0 (no change)
        sensitivity = self.sensitivity
        factor = 1.5 - (sensitivity - 1) * (1.0 / 9.0)  # 1.5 down to 0.5
        return max(5, int(base * factor))

    def _get_min_cv(self) -> float:
        """Return the minimum coefficient of variation, scaled by sensitivity."""
        # Higher sensitivity = more tolerant of low variance (lower threshold)
        # sens 1: 0.04  (very lenient, only catches perfect bots)
        # sens 5: 0.08  (default)
        # sens 10: 0.15 (strict, catches more sophisticated clickers)
        return 0.04 + (self.sensitivity - 1) * (0.11 / 9.0)

    # ------------------------------------------------------------------
    # Entity-hit CPS tracking (on_damage)
    # ------------------------------------------------------------------

    def on_damage(self, event):
        """Track attack frequency against entities for CPS calculation."""
        # ATTACKER is event.damager, not event.actor
        actor = getattr(event, 'damager', None)
        if actor is None or not hasattr(actor, 'unique_id'):
            return
        if not hasattr(actor, 'game_mode'):
            return
        if self.plugin.security.is_level4(actor):
            return

        uuid_str = str(actor.unique_id)
        now = time.time()

        clicks = self._hit_data.setdefault(uuid_str, deque())
        clicks.append(now)

        # Prune old clicks
        while clicks and (now - clicks[0]) > self.WINDOW_SIZE:
            clicks.popleft()

        cps = len(clicks)
        max_cps = self._get_max_cps(uuid_str)
        platform = self._platform.get(uuid_str, "pc")

        flagged = False

        # CPS check
        if cps > max_cps:
            flagged = True
            try:
                event.cancelled = True
            except Exception:
                pass
            self._flags[uuid_str] += 1
            cps_dev = self.record_baseline(actor, "combat.click_rate", float(cps))
            severity = 3
            evidence = {
                "type": "cps",
                "desc": f"Clicking at {cps} CPS (max {max_cps} for {platform})",
                "cps": cps,
                "max": max_cps,
                "platform": platform,
            }
            if cps_dev and cps_dev.is_deviation:
                severity = 4
                evidence["baseline_deviation"] = cps_dev.z_score
            self.emit(actor, severity, evidence, action_hint="cancel")
        else:
            # Record normal click rate baseline (even under threshold)
            self.record_baseline(actor, "combat.click_rate", float(cps))

        # Consistency check (only when enough samples)
        if not flagged and len(clicks) >= self.MIN_CLICKS_FOR_CV:
            intervals = [clicks[i] - clicks[i - 1] for i in range(1, len(clicks))]
            if intervals:
                mean_interval = statistics.mean(intervals)
                if mean_interval > 0:
                    std_interval = statistics.stdev(intervals) if len(intervals) > 1 else 0
                    cv = std_interval / mean_interval
                    min_cv = self._get_min_cv()
                    if cv < min_cv:
                        flagged = True
                        self._flags[uuid_str] += 1
                        effective_cps = round(1.0 / mean_interval, 1) if mean_interval > 0 else 0
                        self.emit(actor, 4, {
                            "type": "consistency",
                            "desc": f"Click timing too consistent (CV={cv:.3f}, min={min_cv:.3f}) at ~{effective_cps} CPS",
                            "cv": f"{cv:.3f}",
                            "min_cv": f"{min_cv:.3f}",
                            "cps": effective_cps,
                            "platform": platform,
                        }, action_hint="cancel")

        if flagged:
            self._hit_data[uuid_str].clear()

    # ------------------------------------------------------------------
    # Air-click tracking via packets (PlayerAuthInputPacket)
    # ------------------------------------------------------------------

    def on_packet(self, event):
        """
        Monitor PlayerAuthInputPacket for air-click detection.
        The packet contains InputData flags; bit 2 (0x4) = LeftClick (attack/mine).
        We track these even when the player isn't hitting an entity.
        """
        if not hasattr(event, 'packet'):
            return
        pkt = event.packet
        pkt_type = type(pkt).__name__

        if pkt_type != "PlayerAuthInputPacket":
            return

        player = event.player if hasattr(event, 'player') else None
        if player is None:
            return
        if self.plugin.security.is_level4(player):
            return

        # Try to extract InputData flags
        input_data = getattr(pkt, 'input_data', None) or getattr(pkt, 'input_flags', None)
        if input_data is None:
            return

        # Bit 2 (0x4) = LeftClick / Attack action
        try:
            flags = int(input_data)
        except (TypeError, ValueError):
            return

        if not (flags & 0x4):  # not clicking
            return

        uuid_str = str(player.unique_id)
        now = time.time()

        clicks = self._air_data.setdefault(uuid_str, deque())
        clicks.append(now)

        while clicks and (now - clicks[0]) > self.AIR_WINDOW:
            clicks.popleft()

        air_cps = len(clicks)
        max_cps = self._get_max_cps(uuid_str)
        platform = self._platform.get(uuid_str, "pc")

        if air_cps > max_cps:
            self._flags[uuid_str] += 1
            self.alert_admins(
                f"§c{player.name}§e flagged for AutoClicker (air-clicking) "
                f"(CPS={air_cps}/{max_cps}, platform={platform})"
            )
            self._air_data[uuid_str].clear()

        # Consistency check on air clicks too
        elif len(clicks) >= self.MIN_CLICKS_FOR_CV:
            intervals = [clicks[i] - clicks[i - 1] for i in range(1, len(clicks))]
            if intervals:
                mean_interval = statistics.mean(intervals)
                if mean_interval > 0:
                    std_interval = statistics.stdev(intervals) if len(intervals) > 1 else 0
                    cv = std_interval / mean_interval
                    min_cv = self._get_min_cv()
                    if cv < min_cv:
                        self._flags[uuid_str] += 1
                        effective_cps = round(1.0 / mean_interval, 1) if mean_interval > 0 else 0
                        self.alert_admins(
                            f"§c{player.name}§e flagged for AutoClicker (air-click consistency) "
                            f"(CV={cv:.3f}<{min_cv:.3f}, ~{effective_cps} CPS, platform={platform})"
                        )
                        self._air_data[uuid_str].clear()
