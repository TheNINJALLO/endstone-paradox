# xray.py - X-Ray detection via weighted suspicion scoring
# Tracks ore mining patterns with multiple detection signals:
#   - Weighted suspicion per ore rarity
#   - Hidden ore detection (ores surrounded by solid blocks)
#   - Vein-jumping detection (mining ores far apart rapidly)
#   - Ore ratio analysis (rare-to-total ratio in time window)
#   - Suspicion decay (natural reduction over time)
#   - Graduated escalation (alert → priority → freeze)

import math
import time
from collections import defaultdict
from endstone_paradox.modules.base import BaseModule

# ═══════════════════════════════════════════════════════════
#  CONFIGURATION
# ═══════════════════════════════════════════════════════════

# All ores we track
TRACKED_ORES = {
    "iron_ore", "deepslate_iron_ore",
    "gold_ore", "deepslate_gold_ore",
    "lapis_ore", "deepslate_lapis_ore",
    "redstone_ore", "deepslate_redstone_ore",
    "diamond_ore", "deepslate_diamond_ore",
    "emerald_ore", "deepslate_emerald_ore",
    "ancient_debris",
}

# Suspicion weight per ore type (rarer ores = more suspicion)
ORE_WEIGHT = {
    "iron_ore": 1, "deepslate_iron_ore": 1,
    "gold_ore": 2, "deepslate_gold_ore": 2,
    "lapis_ore": 1, "deepslate_lapis_ore": 1,
    "redstone_ore": 1, "deepslate_redstone_ore": 1,
    "diamond_ore": 5, "deepslate_diamond_ore": 5,
    "emerald_ore": 5, "deepslate_emerald_ore": 5,
    "ancient_debris": 8,
}


class XrayModule(BaseModule):
    name = "xray"
    check_interval = 20  # 1 second — used for suspicion decay tick

    # Base thresholds (at sensitivity 5)
    BASE_ALERT_SCORE = 15
    BASE_PRIORITY_SCORE = 25
    BASE_FREEZE_SCORE = 40
    BASE_WINDOW_SECONDS = 120.0       # 2-minute ratio window
    BASE_DECAY_INTERVAL = 30.0        # decay every 30s
    BASE_DECAY_AMOUNT = 3             # reduce by 3 per interval
    BASE_VEIN_JUMP_DIST = 12          # blocks between separate ore veins

    NOTIFY_COOLDOWN = 30.0            # don't spam alerts

    def on_start(self):
        self._profiles = {}       # uuid -> MiningProfile dict
        self._last_notify = {}    # uuid -> {level: timestamp}
        self._apply_sensitivity()

    def _apply_sensitivity(self):
        self.ALERT_SCORE = max(5, int(self._scale(self.BASE_ALERT_SCORE)))
        self.PRIORITY_SCORE = max(10, int(self._scale(self.BASE_PRIORITY_SCORE)))
        self.FREEZE_SCORE = max(15, int(self._scale(self.BASE_FREEZE_SCORE)))
        self.WINDOW_SECONDS = self._scale(self.BASE_WINDOW_SECONDS)
        self.DECAY_INTERVAL = self.BASE_DECAY_INTERVAL
        self.DECAY_AMOUNT = self.BASE_DECAY_AMOUNT
        self.VEIN_JUMP_DIST = self._scale(self.BASE_VEIN_JUMP_DIST)

    def on_stop(self):
        self._profiles.clear()
        self._last_notify.clear()

    def on_player_leave(self, player):
        uuid_str = str(player.unique_id)
        self._profiles.pop(uuid_str, None)
        self._last_notify.pop(uuid_str, None)

    # ─── Profile Management ──────────────────────────────

    def _get_profile(self, uuid_str):
        profile = self._profiles.get(uuid_str)
        if not profile:
            now = time.time()
            profile = {
                "suspicion": 0,
                "last_decay": now,
                "total_blocks": 0,
                "rare_blocks": 0,
                "window_start": now,
                "window_blocks": 0,
                "window_rare": 0,
                "last_ore_pos": None,    # (x, y, z)
                "last_ore_time": 0,
                "vein_chain": 0,
            }
            self._profiles[uuid_str] = profile
        return profile

    # ─── Suspicion Decay (runs every check_interval) ─────

    def check(self):
        now = time.time()
        for uuid_str, profile in list(self._profiles.items()):
            elapsed = now - profile["last_decay"]
            if elapsed >= self.DECAY_INTERVAL:
                intervals = int(elapsed / self.DECAY_INTERVAL)
                profile["suspicion"] = max(
                    0, profile["suspicion"] - intervals * self.DECAY_AMOUNT
                )
                profile["last_decay"] += intervals * self.DECAY_INTERVAL

    # ─── Block Break Handler ─────────────────────────────

    def on_block_break(self, event):
        player = event.player
        if player is None:
            return
        if self.plugin.security.is_level4(player):
            return

        block = event.block
        block_type = str(block.type).lower().replace("minecraft:", "")
        uuid_str = str(player.unique_id)
        profile = self._get_profile(uuid_str)
        now = time.time()

        # Decay before processing
        elapsed = now - profile["last_decay"]
        if elapsed >= self.DECAY_INTERVAL:
            intervals = int(elapsed / self.DECAY_INTERVAL)
            profile["suspicion"] = max(
                0, profile["suspicion"] - intervals * self.DECAY_AMOUNT
            )
            profile["last_decay"] += intervals * self.DECAY_INTERVAL

        # Count all blocks for ratio
        profile["total_blocks"] += 1
        profile["window_blocks"] += 1

        # Reset window if expired
        if now - profile["window_start"] > self.WINDOW_SECONDS:
            profile["window_start"] = now
            profile["window_blocks"] = 1
            profile["window_rare"] = 0

        # Only apply detection logic for tracked ores
        if block_type not in TRACKED_ORES:
            return

        profile["rare_blocks"] += 1
        profile["window_rare"] += 1

        weight = ORE_WEIGHT.get(block_type, 1)

        # Signal 1: Hidden ore detection
        if self._is_hidden_ore(block) and weight >= 3:
            self._add_suspicion(
                uuid_str, player, profile, weight + 2,
                f"Hidden ore mined ({block_type})"
            )

        # Signal 2: Ore ratio analysis
        self._check_ore_ratio(uuid_str, player, profile, block_type, weight)

        # Signal 3: Vein-jumping detection
        loc = player.location
        self._check_vein_jump(
            uuid_str, player, profile,
            (loc.x, loc.y, loc.z), block_type, weight
        )

        # Signal 4: Ancient debris burst
        if block_type == "ancient_debris":
            if profile["last_ore_time"] and (now - profile["last_ore_time"]) < 45:
                self._add_suspicion(
                    uuid_str, player, profile, weight + 3,
                    "Ancient debris burst mining"
                )

        profile["last_ore_time"] = now

    # ─── Detection Signals ───────────────────────────────

    def _is_hidden_ore(self, block):
        """Check if ore is surrounded by solid blocks on all 6 faces."""
        try:
            for face in ["north", "south", "east", "west", "above", "below"]:
                neighbor = getattr(block, face, None)
                if neighbor is None:
                    continue
                if callable(neighbor):
                    neighbor = neighbor()
                if neighbor is None:
                    continue
                block_id = str(neighbor.type).lower()
                if "air" in block_id:
                    return False
            return True
        except Exception:
            return False

    def _check_ore_ratio(self, uuid_str, player, profile, block_type, weight):
        """Flag if rare-to-total mining ratio is suspiciously high."""
        if profile["window_blocks"] < 20:
            return  # Not enough data

        ratio = profile["window_rare"] / profile["window_blocks"]

        # Record baseline for ore ratio
        self.record_baseline(player, "mining.ore_ratio", ratio)

        # Thresholds scale with ore rarity
        if weight >= 5:
            threshold_high = 0.08
            threshold_med = 0.05
        else:
            threshold_high = 0.15
            threshold_med = 0.08

        if ratio > threshold_high:
            self._add_suspicion(
                uuid_str, player, profile, weight + 2,
                f"High ore ratio ({block_type}, {ratio:.0%})"
            )
        elif ratio > threshold_med:
            self._add_suspicion(
                uuid_str, player, profile, weight,
                f"Elevated ore ratio ({block_type}, {ratio:.0%})"
            )

    def _check_vein_jump(self, uuid_str, player, profile, loc, block_type, weight):
        """Detect rapid mining of ores far apart (classic X-ray pattern)."""
        last = profile["last_ore_pos"]
        if last is None:
            profile["last_ore_pos"] = loc
            profile["vein_chain"] = 0
            return

        dx = loc[0] - last[0]
        dy = loc[1] - last[1]
        dz = loc[2] - last[2]
        distance = math.sqrt(dx * dx + dy * dy + dz * dz)

        # Record baseline for vein jump distance
        vein_dev = self.record_baseline(player, "mining.vein_jump_dist", distance)

        if distance > self.VEIN_JUMP_DIST:
            profile["vein_chain"] += 1
            if profile["vein_chain"] >= 3:
                extra = 3
                # Extra suspicion if vein jump distance deviates from baseline
                if vein_dev and vein_dev.is_deviation:
                    extra += 2
                self._add_suspicion(
                    uuid_str, player, profile, weight + extra,
                    f"Vein jumping ({block_type}, {distance:.0f}blocks)"
                )
                profile["vein_chain"] = 0
        else:
            profile["vein_chain"] = 0

        profile["last_ore_pos"] = loc

    # ─── Suspicion & Escalation ──────────────────────────

    def _add_suspicion(self, uuid_str, player, profile, amount, reason):
        """Add suspicion and escalate if thresholds are crossed."""
        profile["suspicion"] += amount
        score = profile["suspicion"]

        if score >= self.FREEZE_SCORE:
            self._escalate_freeze(uuid_str, player, profile, reason)
        elif score >= self.PRIORITY_SCORE:
            self._escalate_alert(uuid_str, player, score, "§6[Priority]", reason)
        elif score >= self.ALERT_SCORE:
            self._escalate_alert(uuid_str, player, score, "§e[Alert]", reason)

    def _escalate_alert(self, uuid_str, player, score, level, reason):
        """Send alert to admins (with cooldown)."""
        now = time.time()
        notifs = self._last_notify.setdefault(uuid_str, {})
        last = notifs.get(level, 0)
        if now - last < self.NOTIFY_COOLDOWN:
            return
        notifs[level] = now

        self.emit(player, 2 if level == "§e[Alert]" else 3, {
            "score": score,
            "reason": reason,
            "level": level,
        })

    def _escalate_freeze(self, uuid_str, player, profile, reason):
        """Freeze the player via slowness + mining fatigue."""
        now = time.time()
        notifs = self._last_notify.setdefault(uuid_str, {})
        last = notifs.get("freeze", 0)
        if now - last < self.NOTIFY_COOLDOWN:
            return
        notifs["freeze"] = now

        try:
            self.plugin.server.dispatch_command(
                self.plugin.server.command_sender,
                f'effect "{player.name}" slowness 5 255 true'
            )
            self.plugin.server.dispatch_command(
                self.plugin.server.command_sender,
                f'effect "{player.name}" mining_fatigue 5 255 true'
            )
        except Exception:
            pass

        self.emit(player, 5, {
            "score": profile['suspicion'],
            "reason": reason,
            "action": "freeze",
        })
        # Reset score after freeze so it can rebuild
        profile["suspicion"] = max(0, profile["suspicion"] - self.FREEZE_SCORE // 2)
