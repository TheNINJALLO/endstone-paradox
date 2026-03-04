# stephack.py - Step Hack detection
# Detects players stepping up full blocks without jumping.

import time
from endstone import GameMode
from endstone_paradox.modules.base import BaseModule


class StepHackModule(BaseModule):
    """Detects step hack (stepping up full blocks without jumping).

    A legitimate player must jump (Y velocity spike + jump event) to go up
    a full block. Step hacks allow instant Y+1 without a jump flag.
    """

    name = "stephack"
    check_interval = 5  # 0.25 seconds for precision

    STEP_THRESHOLD = 0.6  # Y increase per check that requires a jump
    FLAGS_REQUIRED = 3     # consecutive step-ups without jump before flag

    def on_start(self):
        self._player_data = {}  # uuid -> {last_y, step_flags}

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
                if player.is_gliding or player.is_in_water:
                    continue
                if self.plugin.is_player_climbing(player):
                    continue

                uuid_str = str(player.unique_id)
                loc = player.location
                data = self._player_data.setdefault(uuid_str, {
                    "last_y": loc.y,
                    "step_flags": 0,
                })

                y_delta = loc.y - data["last_y"]
                data["last_y"] = loc.y

                # Only care about upward movement
                if y_delta < self.STEP_THRESHOLD:
                    data["step_flags"] = max(0, data["step_flags"] - 1)
                    continue

                # Player went up significantly — did they jump?
                if self.plugin.is_player_jumping(player):
                    data["step_flags"] = 0
                    continue

                # On slime/honey blocks, bouncing is legit
                try:
                    dim = player.dimension
                    below = dim.get_block_at(int(loc.x), int(loc.y) - 1, int(loc.z))
                    if below:
                        bt = str(below.type).lower()
                        if "slime" in bt or "honey" in bt:
                            data["step_flags"] = 0
                            continue
                except Exception:
                    pass

                # On stairs/slabs, half-block step-ups are normal
                if y_delta < 0.55:
                    continue

                data["step_flags"] += 1
                if data["step_flags"] >= self.FLAGS_REQUIRED:
                    self.emit(player, 3, {
                        "type": "step_hack",
                        "y_delta": f"{y_delta:.2f}",
                        "flags": data["step_flags"],
                    }, action_hint="setback")
                    data["step_flags"] = 0

            except Exception:
                pass
