# waterwalk.py - Jesus / WaterWalk detection
# Detects players standing on water without Frost Walker or lily pads.

import time
from endstone import GameMode
from endstone_paradox.modules.base import BaseModule


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

                # Check block at feet and below feet
                feet_y = int(loc.y) - 1
                try:
                    block_below = dim.get_block_at(int(loc.x), feet_y, int(loc.z))
                    if block_below is None:
                        continue

                    below_type = str(block_below.type).lower().replace("minecraft:", "")

                    # Check if standing on water
                    if "water" not in below_type and "flowing_water" not in below_type:
                        data["flags"] = max(0, data["flags"] - 1)
                        continue

                    # Check for safe blocks nearby (lily pad, ice, etc.)
                    safe = False
                    for dy in range(-1, 2):
                        for dx in range(-1, 2):
                            for dz in range(-1, 2):
                                try:
                                    b = dim.get_block_at(
                                        int(loc.x) + dx,
                                        feet_y + dy,
                                        int(loc.z) + dz,
                                    )
                                    if b:
                                        bt = str(b.type).lower().replace("minecraft:", "")
                                        for ws in self.WATER_SAFE:
                                            if ws in bt:
                                                safe = True
                                                break
                                    if safe:
                                        break
                                except Exception:
                                    pass
                            if safe:
                                break
                        if safe:
                            break

                    if safe:
                        data["flags"] = max(0, data["flags"] - 1)
                        continue

                    # Standing on water with no safe blocks nearby
                    data["flags"] += 1
                    if data["flags"] >= self.FLAGS_REQUIRED:
                        self.emit(player, 3, {
                            "type": "waterwalk",
                            "flags": data["flags"],
                        }, action_hint="setback")
                        data["flags"] = 0

                except Exception:
                    pass

            except Exception:
                pass
