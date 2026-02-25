# scaffold.py - Detects speed-bridging via placement rate + axis patterns

import time
from collections import deque
from endstone_paradox.modules.base import BaseModule


class ScaffoldModule(BaseModule):
    """Detects scaffold hacks via block placement pattern analysis."""

    name = "scaffold"

    MAX_PLACEMENTS = 12      # Max blocks in the time window (fast builders can do 8+/s)
    TIME_WINDOW = 1.5        # Seconds
    AXIS_THRESHOLD = 3       # All 3 axes must be constant to flag (very strict = fewer FPs)

    def on_start(self):
        self._placement_data = {}  # UUID -> deque of (time, x, y, z)

    def on_stop(self):
        self._placement_data.clear()

    def on_player_leave(self, player):
        self._placement_data.pop(str(player.unique_id), None)

    def on_block_place(self, event):
        """Track block placements for scaffold detection."""
        player = event.player
        if player is None:
            return
        if self.plugin.security.is_level4(player):
            return

        uuid_str = str(player.unique_id)
        now = time.time()
        block = event.block

        placements = self._placement_data.setdefault(uuid_str, deque())
        placements.append((now, block.x, block.y, block.z))

        # Remove old placements
        while placements and (now - placements[0][0]) > self.TIME_WINDOW:
            placements.popleft()

        if len(placements) < self.MAX_PLACEMENTS:
            return

        # Check for scaffold pattern: two axes remain constant
        placement_list = list(placements)
        xs = set(p[1] for p in placement_list)
        ys = set(p[2] for p in placement_list)
        zs = set(p[3] for p in placement_list)

        constant_axes = 0
        if len(xs) <= 2:
            constant_axes += 1
        if len(ys) <= 2:
            constant_axes += 1
        if len(zs) <= 2:
            constant_axes += 1

        if constant_axes >= self.AXIS_THRESHOLD:
            # Cancel the placement
            event.is_cancelled = True

            self.alert_admins(
                f"§c{player.name}§e flagged for Scaffolding "
                f"({len(placements)} blocks in {self.TIME_WINDOW}s)"
            )
            self._placement_data[uuid_str].clear()
