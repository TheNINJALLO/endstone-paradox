# fly.py - Flight/hover detection with surrounding block validation
# Checks 8 surrounding blocks below to ensure majority are air before flagging.
# Validates player is within dimension height range.

import math
from endstone import GameMode
from endstone_paradox.modules.base import BaseModule


class FlyModule(BaseModule):
    name = "fly"
    check_interval = 20  # 1s

    # Base thresholds (at sensitivity 5)
    BASE_V_THRESHOLD = 0.15
    BASE_H_THRESHOLD = 0.15
    BASE_HOVER_THRESHOLD = 2  # seconds

    def on_start(self):
        self._player_data = {}  # uuid -> {landing, hover_time, trident_used}
        self._apply_sensitivity()

    def _apply_sensitivity(self):
        self.v_threshold = self._scale(self.BASE_V_THRESHOLD)
        self.h_threshold = self._scale(self.BASE_H_THRESHOLD)
        self.hover_threshold = self._scale(self.BASE_HOVER_THRESHOLD)

    def on_stop(self):
        self._player_data.clear()

    def on_player_leave(self, player):
        self._player_data.pop(str(player.unique_id), None)

    def check(self):
        for player in self.plugin.server.online_players:
            try:
                self._check_player(player)
            except Exception:
                pass

    def _check_player(self, player):
        uuid_str = str(player.unique_id)

        # skip creative/spectator/admins
        if player.game_mode in (GameMode.CREATIVE, GameMode.SPECTATOR):
            return
        if self.plugin.security.is_level4(player):
            return

        if player.is_gliding or player.is_in_water:
            return
        if self.plugin.is_player_climbing(player):
            return

        data = self._player_data.setdefault(uuid_str, {
            "landing": None,
            "hover_time": 0,
            "trident_used": False,
        })

        # trident riptide exemption
        if data["trident_used"]:
            data["trident_used"] = False
            return

        loc = player.location

        if player.is_on_ground:
            data["landing"] = loc
            data["hover_time"] = 0
            return

        # recently jumped = legit air time
        if self.plugin.is_player_jumping(player):
            return

        # ── Surrounding block check ──
        # Check 8 blocks below + center for air majority
        # Avoids false positives near stairs, edges, half-slabs
        if not self._majority_air_below(player):
            data["hover_time"] = 0
            return

        vel = player.velocity
        h_speed = math.sqrt(vel.x ** 2 + vel.z ** 2)

        is_suspicious = (
            (player.is_flying and not player.is_on_ground) or
            (abs(vel.y) >= self.v_threshold or h_speed >= self.h_threshold)
        )

        if is_suspicious and not player.is_on_ground:
            data["hover_time"] += 1

            if data["hover_time"] >= self.hover_threshold:
                landing = data.get("landing")
                if landing:
                    player.teleport(landing)
                    self.alert_admins(
                        f"§c{player.name}§e was detected flying and teleported back."
                    )
                data["hover_time"] = 0
        else:
            data["hover_time"] = max(0, data["hover_time"] - 1)

    def _majority_air_below(self, player):
        """
        Check if the majority of the 9 blocks below the player
        (center + 8 surrounding) are air. Returns True if majority air.
        Only flags fly if player is genuinely over open air.
        """
        try:
            loc = player.location
            dim = player.dimension

            # Validate within dimension height range
            try:
                height_range = dim.height_range if hasattr(dim, 'height_range') else None
                if height_range:
                    if loc.y < height_range[0] or loc.y >= height_range[1]:
                        return False
            except Exception:
                pass

            # Get block at player's feet, then check below it
            block_at = dim.get_block_at(int(loc.x), int(loc.y) - 1, int(loc.z))
            if block_at is None:
                return False

            air_count = 0
            total = 0
            offsets = [
                (0, 0), (1, 0), (-1, 0), (0, 1), (0, -1),
                (1, 1), (1, -1), (-1, 1), (-1, -1)
            ]

            for dx, dz in offsets:
                try:
                    check_block = dim.get_block_at(
                        int(loc.x) + dx, int(loc.y) - 1, int(loc.z) + dz
                    )
                    total += 1
                    if check_block is not None:
                        block_id = str(check_block.type).lower()
                        if "air" in block_id:
                            air_count += 1
                    else:
                        air_count += 1
                except Exception:
                    total += 1
                    air_count += 1  # Can't check = assume air

            # Majority (>50%) must be air to flag
            return air_count > total / 2

        except Exception:
            return False

    def set_trident_used(self, player):
        uuid_str = str(player.unique_id)
        data = self._player_data.get(uuid_str)
        if data:
            data["trident_used"] = True
