# waterwalk.py - Jesus / WaterWalk detection
# Detects players standing on water without Frost Walker or lily pads.

import math
import time
from endstone import GameMode
from endstone_paradox.modules.base import BaseModule


def _is_solid_support(block_type_str: str) -> bool:
    """Return True if a block type is a solid, non-water, non-air block."""
    return ("water" not in block_type_str
            and "flowing_water" not in block_type_str
            and "air" not in block_type_str)


class WaterWalkModule(BaseModule):
    """Detects players walking on water (Jesus hack).

    Checks if a player is standing on_ground=true but the block below is water
    and there's no lily pad, ice, or Frost Walker boots.
    """

    name = "waterwalk"
    check_interval = 20  # 1 second

    FLAGS_REQUIRED = 4  # consecutive water-standing checks before flag

    # Blocks that legitimately allow standing on/near water
    WATER_SAFE = {
        "ice", "packed_ice", "blue_ice", "frosted_ice",
        "lily_pad", "waterlily",
        "boat",
        "kelp", "seagrass",
        "dripleaf", "big_dripleaf",
    }

    def on_start(self):
        self._player_data = {}  # uuid -> {flags: int}

    def on_stop(self):
        self._player_data.clear()

    def on_player_leave(self, player):
        self._player_data.pop(str(player.unique_id), None)

    # ------------------------------------------------------------------
    # Support helpers
    # ------------------------------------------------------------------

    def _has_solid_support(self, dim, loc) -> bool:
        """Check whether any block under/around the player's feet is solid.

        Samples the player's 4 foot-corners PLUS a 1-block horizontal
        ring at two Y levels (foot block and below) so that standing on
        a solid block adjacent to water is never flagged.
        """
        # Use math.floor for correct negative-coordinate rounding
        px = math.floor(loc.x)
        pz = math.floor(loc.z)
        feet_y = math.floor(loc.y) - 1

        HALF_WIDTH = 0.3
        # Foot-corner block coords (the 4 blocks the hitbox overlaps)
        corner_xs = {math.floor(loc.x - HALF_WIDTH), math.floor(loc.x + HALF_WIDTH)}
        corner_zs = {math.floor(loc.z - HALF_WIDTH), math.floor(loc.z + HALF_WIDTH)}

        # Build unique XZ set: foot corners + 1-block ring around player
        sample_xz = set()
        for cx in corner_xs:
            for cz in corner_zs:
                sample_xz.add((cx, cz))
        for dx in range(-1, 2):
            for dz in range(-1, 2):
                sample_xz.add((px + dx, pz + dz))

        # Check two Y levels: the block below the player and the block
        # at foot level (handles slabs, farmland, soul sand, etc.)
        for sy in (feet_y, feet_y + 1):
            for sx, sz in sample_xz:
                try:
                    fb = dim.get_block_at(sx, sy, sz)
                    if fb:
                        ft = str(fb.type).lower().replace("minecraft:", "")
                        if _is_solid_support(ft):
                            return True
                except Exception:
                    pass
        return False

    def _has_safe_block_nearby(self, dim, loc, feet_y) -> bool:
        """Check for safe blocks (lily pad, ice, etc.) in a 3×3×3 area."""
        px = math.floor(loc.x)
        pz = math.floor(loc.z)
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                for dz in range(-1, 2):
                    try:
                        b = dim.get_block_at(px + dx, feet_y + dy, pz + dz)
                        if b:
                            bt = str(b.type).lower().replace("minecraft:", "")
                            for ws in self.WATER_SAFE:
                                if ws in bt:
                                    return True
                    except Exception:
                        pass
        return False

    # ------------------------------------------------------------------
    # Main check
    # ------------------------------------------------------------------

    def check(self):
        for player in self.plugin.server.online_players:
            try:
                if player.game_mode in (GameMode.CREATIVE, GameMode.SPECTATOR):
                    continue
                if self.plugin.security.is_level4(player):
                    continue
                if player.is_in_water or player.is_gliding:
                    continue

                uuid_str = str(player.unique_id)
                data = self._player_data.setdefault(uuid_str, {"flags": 0})

                if not player.is_on_ground:
                    data["flags"] = max(0, data["flags"] - 1)
                    continue

                loc = player.location
                dim = player.dimension
                feet_y = math.floor(loc.y) - 1

                # --- Solid support check ---
                # If any block under/around the player is solid the
                # player is legitimately standing on a real surface.
                if self._has_solid_support(dim, loc):
                    data["flags"] = max(0, data["flags"] - 1)
                    continue

                try:
                    block_below = dim.get_block_at(
                        math.floor(loc.x), feet_y, math.floor(loc.z)
                    )
                    if block_below is None:
                        continue

                    below_type = str(block_below.type).lower().replace("minecraft:", "")

                    # Not standing over water at all → no concern
                    if "water" not in below_type and "flowing_water" not in below_type:
                        data["flags"] = max(0, data["flags"] - 1)
                        continue

                    # Check for safe blocks nearby (lily pad, ice, etc.)
                    if self._has_safe_block_nearby(dim, loc, feet_y):
                        data["flags"] = max(0, data["flags"] - 1)
                        continue

                    # Standing on water with no safe or solid blocks nearby
                    data["flags"] += 1
                    if data["flags"] >= self.FLAGS_REQUIRED:
                        self.emit(player, 3, {
                            "type": "waterwalk",
                            "desc": "Standing on water with no solid or safe blocks nearby",
                            "flags": data["flags"],
                        }, action_hint="setback")
                        data["flags"] = 0

                except Exception:
                    pass

            except Exception:
                pass
