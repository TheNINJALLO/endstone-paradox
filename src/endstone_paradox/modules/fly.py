# fly.py - Flight/hover detection
# Tracks ground state, velocity, and hover time. Teleports cheaters back.

import math
from endstone import GameMode
from endstone_paradox.modules.base import BaseModule


class FlyModule(BaseModule):
    name = "fly"
    check_interval = 20  # 1s

    def on_start(self):
        self._player_data = {}  # uuid -> {landing, hover_time, trident_used}

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

        vel = player.velocity
        h_speed = math.sqrt(vel.x ** 2 + vel.z ** 2)
        v_threshold = 0.5
        h_threshold = 0.5
        hover_threshold = 5  # seconds

        is_suspicious = (
            (player.is_flying and not player.is_on_ground) or
            (abs(vel.y) >= v_threshold or h_speed >= h_threshold)
        )

        if is_suspicious and not player.is_on_ground:
            data["hover_time"] += 1

            if data["hover_time"] >= hover_threshold:
                landing = data.get("landing")
                if landing:
                    player.teleport(landing)
                    self.alert_admins(
                        f"§c{player.name}§e was detected flying and teleported back."
                    )
                data["hover_time"] = 0
        else:
            data["hover_time"] = max(0, data["hover_time"] - 1)

    def set_trident_used(self, player):
        uuid_str = str(player.unique_id)
        data = self._player_data.get(uuid_str)
        if data:
            data["trident_used"] = True
