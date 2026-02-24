"""
Paradox AntiCheat - X-Ray Detection Module

Detects X-ray by monitoring the rate of ore blocks broken per time window.
Uses configurable thresholds per ore type.
"""

import time
from collections import defaultdict
from endstone_paradox.modules.base import BaseModule


class XrayModule(BaseModule):
    """Detects X-ray hacks via ore mining rate analysis."""

    name = "xray"

    TIME_WINDOW = 300.0  # 5 minutes
    NOTIFY_COOLDOWN = 60.0  # Don't re-alert for same player within 60s

    # Ore thresholds: max blocks per TIME_WINDOW before alert
    ORE_THRESHOLDS = {
        "diamond_ore": 10,
        "deepslate_diamond_ore": 10,
        "ancient_debris": 5,
        "emerald_ore": 12,
        "deepslate_emerald_ore": 12,
        "gold_ore": 15,
        "deepslate_gold_ore": 15,
        "nether_gold_ore": 20,
        "iron_ore": 25,
        "deepslate_iron_ore": 25,
        "lapis_ore": 15,
        "deepslate_lapis_ore": 15,
        "redstone_ore": 20,
        "deepslate_redstone_ore": 20,
    }

    def on_start(self):
        self._mine_data = {}     # UUID -> {ore_type: [timestamps]}
        self._last_notify = {}   # UUID -> timestamp

    def on_stop(self):
        self._mine_data.clear()
        self._last_notify.clear()

    def on_player_leave(self, player):
        uuid_str = str(player.unique_id)
        self._mine_data.pop(uuid_str, None)
        self._last_notify.pop(uuid_str, None)

    def on_block_break(self, event):
        """Monitor ore block breaks."""
        player = event.player
        if player is None:
            return
        if self.plugin.security.is_level4(player):
            return

        block = event.block
        block_type = str(block.type).lower().replace("minecraft:", "")

        if block_type not in self.ORE_THRESHOLDS:
            return

        uuid_str = str(player.unique_id)
        now = time.time()

        # Track the break
        player_data = self._mine_data.setdefault(uuid_str, defaultdict(list))
        timestamps = player_data[block_type]
        timestamps.append(now)

        # Clean old entries
        while timestamps and (now - timestamps[0]) > self.TIME_WINDOW:
            timestamps.pop(0)

        threshold = self.ORE_THRESHOLDS[block_type]
        if len(timestamps) >= threshold:
            # Check notification cooldown
            last = self._last_notify.get(uuid_str, 0)
            if now - last >= self.NOTIFY_COOLDOWN:
                self._last_notify[uuid_str] = now
                self.alert_admins(
                    f"§c{player.name}§e suspected X-Ray: "
                    f"mined {len(timestamps)}x {block_type} in "
                    f"{int(self.TIME_WINDOW / 60)}min (threshold: {threshold})"
                )
