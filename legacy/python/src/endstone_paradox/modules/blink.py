# blink.py - Blink / Teleport hack detection
# Detects large position jumps without a server-initiated teleport.

import time
import math
from endstone import GameMode
from endstone_paradox.modules.base import BaseModule


class BlinkModule(BaseModule):
    """Detects blink/teleport hacks (large instant position jumps).

    Flags when a player moves >10 blocks between position checks
    without a corresponding server teleport event.
    Keeps a short teleport exemption window for /tp, ender pearls, etc.
    """

    name = "blink"
    check_interval = 10  # 0.5 seconds

    BLINK_DISTANCE = 10.0   # blocks in one check = suspicious
    FLAGS_REQUIRED = 2       # consecutive jumps (2 = very confident)
    TELEPORT_GRACE = 3.0     # seconds to ignore after a legitimate teleport

    def on_start(self):
        self._player_data = {}  # uuid -> {last_pos, blink_flags, last_teleport}

    def on_stop(self):
        self._player_data.clear()

    def on_player_leave(self, player):
        self._player_data.pop(str(player.unique_id), None)

    def mark_teleport(self, player):
        """Called when a legitimate teleport occurs (command, pearl, portal)."""
        uuid_str = str(player.unique_id)
        data = self._player_data.get(uuid_str)
        if data:
            data["last_teleport"] = time.time()

    def check(self):
        now = time.time()
        for player in self.plugin.server.online_players:
            try:
                if player.game_mode in (GameMode.CREATIVE, GameMode.SPECTATOR):
                    continue
                if self.plugin.security.is_level4(player):
                    continue

                uuid_str = str(player.unique_id)
                loc = player.location
                cur = (loc.x, loc.y, loc.z)

                data = self._player_data.setdefault(uuid_str, {
                    "last_pos": cur,
                    "blink_flags": 0,
                    "last_teleport": 0,
                })

                prev = data["last_pos"]
                data["last_pos"] = cur

                # Skip if recently teleported
                if now - data["last_teleport"] < self.TELEPORT_GRACE:
                    continue

                # Calculate horizontal distance (blink is about lateral teleporting)
                dx = cur[0] - prev[0]
                dy = cur[1] - prev[1]
                dz = cur[2] - prev[2]
                h_dist = math.sqrt(dx*dx + dz*dz)

                # Skip if mostly vertical movement (falling/jumping)
                if abs(dy) > h_dist:
                    data["blink_flags"] = max(0, data["blink_flags"] - 1)
                    continue

                # Always record baseline to learn normal movement distances
                bl = self.record_baseline(player, "blink.h_dist", h_dist)

                if h_dist > self.BLINK_DISTANCE:
                    # Skip if player is gliding (elytra can cover distance fast)
                    if player.is_gliding:
                        continue

                    # During warmup, just learn — don't flag
                    if bl and bl.warming_up:
                        continue

                    data["blink_flags"] += 1
                    if data["blink_flags"] >= self.FLAGS_REQUIRED:
                        # Only emit if baseline confirms this is abnormal
                        if bl and bl.is_deviation:
                            self.emit(player, 4, {
                                "type": "blink",
                                "desc": f"Teleported {h_dist:.1f} blocks instantly (no server TP)",
                                "distance": f"{h_dist:.1f}",
                                "baseline_avg": f"{bl.avg:.1f}",
                                "z_score": bl.z_score,
                            }, action_hint="setback")
                        data["blink_flags"] = 0
                else:
                    data["blink_flags"] = max(0, data["blink_flags"] - 1)

            except Exception:
                pass
