# xray.py - Ore mining rate tracker
# Flags players mining too many ores in a time window.

import time
from collections import defaultdict
from endstone_paradox.modules.base import BaseModule


class XrayModule(BaseModule):
    name = "xray"

    TIME_WINDOW = 300.0    # 5 min window
    NOTIFY_COOLDOWN = 60.0 # don't spam alerts

    # max ore breaks per window before flagging (generous for strip mining)
    ORE_THRESHOLDS = {
        "diamond_ore": 20,
        "deepslate_diamond_ore": 20,
        "ancient_debris": 10,
        "emerald_ore": 24,
        "deepslate_emerald_ore": 24,
        "gold_ore": 30,
        "deepslate_gold_ore": 30,
        "nether_gold_ore": 40,
        "iron_ore": 50,
        "deepslate_iron_ore": 50,
        "lapis_ore": 30,
        "deepslate_lapis_ore": 30,
        "redstone_ore": 40,
        "deepslate_redstone_ore": 40,
    }

    def on_start(self):
        self._mine_data = {}     # uuid -> {ore: [timestamps]}
        self._last_notify = {}   # uuid -> timestamp

    def on_stop(self):
        self._mine_data.clear()
        self._last_notify.clear()

    def on_player_leave(self, player):
        uuid_str = str(player.unique_id)
        self._mine_data.pop(uuid_str, None)
        self._last_notify.pop(uuid_str, None)

    def on_block_break(self, event):
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

        player_data = self._mine_data.setdefault(uuid_str, defaultdict(list))
        timestamps = player_data[block_type]
        timestamps.append(now)

        # clean old
        while timestamps and (now - timestamps[0]) > self.TIME_WINDOW:
            timestamps.pop(0)

        threshold = self.ORE_THRESHOLDS[block_type]
        if len(timestamps) >= threshold:
            last = self._last_notify.get(uuid_str, 0)
            if now - last >= self.NOTIFY_COOLDOWN:
                self._last_notify[uuid_str] = now
                self.alert_admins(
                    f"§c{player.name}§e suspected X-Ray: "
                    f"mined {len(timestamps)}x {block_type} in "
                    f"{int(self.TIME_WINDOW / 60)}min (threshold: {threshold})"
                )
