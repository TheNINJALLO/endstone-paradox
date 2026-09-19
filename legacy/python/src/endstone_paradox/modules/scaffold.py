# scaffold.py - Scaffold detection with smarter filtering
# Only flags blocks placed over air (not normal building), excludes
# scaffolding/farmland, and returns items on detection.

import time
import math
from collections import deque
from endstone_paradox.modules.base import BaseModule

# Blocks that are exempt from scaffold detection
EXCLUDED_BLOCKS = {"scaffolding"}


class ScaffoldModule(BaseModule):
    """Detects scaffold hacks via block placement pattern analysis."""

    name = "scaffold"

    # Base thresholds (at sensitivity 5)
    BASE_MAX_PLACEMENTS = 3       # Placements in quick succession to flag
    BASE_TIME_WINDOW = 1.0        # Seconds (20 ticks)

    def on_start(self):
        self._placement_data = {}  # UUID -> {positions: [(x,y,z)], times: [float]}
        self._apply_sensitivity()

    def _apply_sensitivity(self):
        self.MAX_PLACEMENTS = max(3, int(self._scale(self.BASE_MAX_PLACEMENTS)))
        self.TIME_WINDOW = self._scale(self.BASE_TIME_WINDOW)

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

        block = event.block
        if block is None:
            return

        # Get block type
        block_type = str(block.type).lower().replace("minecraft:", "")

        # Skip excluded blocks (scaffolding itself, etc.)
        if block_type in EXCLUDED_BLOCKS:
            return

        # Skip creative/spectator mode
        from endstone import GameMode
        if player.game_mode in (GameMode.CREATIVE, GameMode.SPECTATOR):
            return

        # Skip sneaking players (bridging while sneaking is legitimate)
        try:
            if player.is_sneaking:
                return
        except Exception:
            pass

        # Key check: Only flag blocks placed OVER AIR
        # If the block below is solid, this is normal building
        try:
            below = block.below() if hasattr(block, 'below') else None
            if below is not None:
                below_type = str(below.type).lower()
                # Skip farmland (crop planting)
                if "farmland" in below_type:
                    return
                # If block below is solid and not excluded, skip
                if "air" not in below_type and below_type not in EXCLUDED_BLOCKS:
                    return
        except Exception:
            pass

        uuid_str = str(player.unique_id)
        now = time.time()

        data = self._placement_data.setdefault(uuid_str, {
            "positions": [],
            "times": [],
        })

        data["positions"].append((block.x, block.y, block.z))
        data["times"].append(now)

        # Limit buffer size
        max_buf = self.MAX_PLACEMENTS * 2
        if len(data["positions"]) > max_buf:
            data["positions"] = data["positions"][-max_buf:]
            data["times"] = data["times"][-max_buf:]

        # Not enough data yet
        if len(data["positions"]) < self.MAX_PLACEMENTS:
            return

        # Check if recent placements are within the time window
        recent_times = data["times"][-self.MAX_PLACEMENTS:]
        if recent_times[-1] - recent_times[0] > self.TIME_WINDOW:
            return

        # Check for scaffold pattern: at least 2 out of 3 axes constant
        recent_pos = data["positions"][-self.MAX_PLACEMENTS:]
        base = recent_pos[0]
        x_match = all(p[0] == base[0] for p in recent_pos)
        y_match = all(p[1] == base[1] for p in recent_pos)
        z_match = all(p[2] == base[2] for p in recent_pos)

        constant_axes = sum([x_match, y_match, z_match])

        if constant_axes >= 2:
            # Check for backwards placement (block behind facing direction)
            backwards = False
            try:
                p_loc = player.location
                if p_loc and hasattr(p_loc, 'yaw'):
                    # Player facing direction (unit vector)
                    yaw_rad = math.radians(p_loc.yaw)
                    face_x = -math.sin(yaw_rad)
                    face_z = math.cos(yaw_rad)
                    # Direction from player to placed block
                    bx = block.x + 0.5 - p_loc.x
                    bz = block.z + 0.5 - p_loc.z
                    # Dot product: negative = behind player
                    dot = face_x * bx + face_z * bz
                    if dot < 0:
                        backwards = True
            except Exception:
                pass

            # Cancel the placement
            try:
                event.is_cancelled = True
            except Exception:
                pass

            # Record placement rate baseline
            rate = self.MAX_PLACEMENTS / max(self.TIME_WINDOW, 0.01)
            rate_dev = self.record_baseline(player, "build.placement_rate", rate)

            severity = 3
            backwards_str = " while facing backwards" if backwards else ""
            evidence = {
                "desc": f"Placed {self.MAX_PLACEMENTS} blocks over air in {self.TIME_WINDOW:.1f}s{backwards_str}",
                "blocks": self.MAX_PLACEMENTS,
                "window": f"{self.TIME_WINDOW:.1f}s",
            }
            if backwards:
                evidence["backwards"] = True
                severity = 4  # backwards placement = stronger signal
            elif rate_dev and rate_dev.is_deviation:
                severity = 4
                evidence["baseline_deviation"] = rate_dev.z_score

            self.emit(player, severity, evidence, action_hint="cancel")
            # Clear data to prevent repeated flagging
            self._placement_data[uuid_str] = {"positions": [], "times": []}
