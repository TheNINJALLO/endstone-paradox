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

                # On slime/honey/scaffolding/ladder/vine, vertical movement is legit
                on_climbable = False
                try:
                    dim = player.dimension
                    ix, iy, iz = int(loc.x), int(loc.y), int(loc.z)
                    for check_y in (iy, iy - 1):
                        bl = dim.get_block_at(ix, check_y, iz)
                        if bl:
                            bt = str(bl.type).lower()
                            if any(s in bt for s in (
                                "slime", "honey", "scaffolding", "scaffold",
                                "ladder", "vine", "cave_vine", "twisting_vine",
                                "weeping_vine",
                            )):
                                on_climbable = True
                                break
                except Exception:
                    pass

                if on_climbable:
                    data["step_flags"] = 0
                    continue

                # On stairs/slabs, half-block step-ups are normal
                if y_delta < 0.55:
                    continue

                # Record baseline to learn normal step-up heights
                bl = self.record_baseline(player, "stephack.y_delta", y_delta)

                # During warmup, just learn — don't flag
                if bl and bl.warming_up:
                    continue

                data["step_flags"] += 1
                if data["step_flags"] >= self.FLAGS_REQUIRED:
                    # Only emit if baseline confirms abnormal step
                    if bl and bl.is_deviation:
                        self.emit(player, 3, {
                            "type": "step_hack",
                            "y_delta": f"{y_delta:.2f}",
                            "flags": data["step_flags"],
                            "z_score": bl.z_score,
                        }, action_hint="setback")
                    data["step_flags"] = 0

            except Exception:
                pass
