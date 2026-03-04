# vision.py - Aimbot/snap detection via yaw/pitch change tracking

import math
import time
from collections import deque
from endstone_paradox.modules.base import BaseModule


class VisionModule(BaseModule):
    """Detects vision anomalies (aimbot, freecam)."""

    name = "vision"
    check_interval = 5  # Check every 0.25 seconds

    # Base thresholds (at sensitivity 5)
    BASE_SNAP_THRESHOLD = 150.0      # Sudden snap angle
    BASE_SNAP_COUNT_LIMIT = 8        # Max snaps in window before flag
    BASE_WINDOW_SIZE = 3.0           # Analysis window (seconds)

    def on_start(self):
        self._rotation_data = {}  # UUID -> {last_yaw, last_pitch, snaps: deque}
        self._apply_sensitivity()

    def _apply_sensitivity(self):
        self.SNAP_THRESHOLD = self._scale(self.BASE_SNAP_THRESHOLD)
        self.SNAP_COUNT_LIMIT = max(3, int(self._scale(self.BASE_SNAP_COUNT_LIMIT)))
        self.WINDOW_SIZE = self._scale(self.BASE_WINDOW_SIZE)

    def on_stop(self):
        self._rotation_data.clear()

    def on_player_leave(self, player):
        self._rotation_data.pop(str(player.unique_id), None)

    def check(self):
        """Track rotation changes for all players."""
        now = time.time()
        for player in self.plugin.server.online_players:
            try:
                if self.plugin.security.is_level4(player):
                    continue

                uuid_str = str(player.unique_id)
                loc = player.location
                yaw = loc.yaw if hasattr(loc, 'yaw') else 0
                pitch = loc.pitch if hasattr(loc, 'pitch') else 0

                data = self._rotation_data.setdefault(uuid_str, {
                    "last_yaw": yaw,
                    "last_pitch": pitch,
                    "snaps": deque(),
                    "last_delta": 0.0,
                    "accel_flags": 0,
                    "last_snap_time": 0,
                })

                # Calculate rotation delta
                d_yaw = abs(((yaw - data["last_yaw"] + 180) % 360) - 180)
                d_pitch = abs(pitch - data["last_pitch"])
                rotation_delta = math.sqrt(d_yaw ** 2 + d_pitch ** 2)

                data["last_yaw"] = yaw
                data["last_pitch"] = pitch

                # Track snaps (sudden rapid rotations)
                if rotation_delta >= self.SNAP_THRESHOLD:
                    data["snaps"].append(now)
                    data["last_snap_time"] = now

                # Rotation acceleration (2nd derivative)
                # Aimbots: very low delta then sudden huge delta = extreme acceleration
                prev_delta = data["last_delta"]
                rotation_accel = abs(rotation_delta - prev_delta)
                data["last_delta"] = rotation_delta

                # Flag extreme acceleration (snap from still to huge movement)
                if prev_delta < 2.0 and rotation_delta > 100.0:
                    data["accel_flags"] += 1
                    if data["accel_flags"] >= 4:  # 4 snap-from-still events
                        self.emit(player, 3, {
                            "type": "aimbot_accel",
                            "accel": f"{rotation_accel:.0f}",
                            "flags": data["accel_flags"],
                        })
                        data["accel_flags"] = 0
                else:
                    data["accel_flags"] = max(0, data["accel_flags"] - 1)

                # Clean old snaps
                while data["snaps"] and (now - data["snaps"][0]) > self.WINDOW_SIZE:
                    data["snaps"].popleft()

                # Flag if too many snaps
                if len(data["snaps"]) >= self.SNAP_COUNT_LIMIT:
                    self.emit(player, 3, {
                        "snaps": len(data['snaps']),
                        "window": f"{self.WINDOW_SIZE:.1f}s",
                    })
                    data["snaps"].clear()
            except Exception:
                pass

    def on_damage(self, event):
        """Check for pre-attack snap (aimbot signature)."""
        attacker = getattr(event, 'damager', None)
        if attacker is None or not hasattr(attacker, 'unique_id'):
            return
        if not hasattr(attacker, 'game_mode'):
            return
        if self.plugin.security.is_level4(attacker):
            return

        uuid_str = str(attacker.unique_id)
        now = time.time()
        data = self._rotation_data.get(uuid_str)
        if data is None:
            return

        # If a snap occurred within 0.3s before this hit, it's suspicious
        time_since_snap = now - data.get("last_snap_time", 0)
        if 0 < time_since_snap < 0.3:
            self.emit(attacker, 4, {
                "type": "snap_attack",
                "snap_delay": f"{time_since_snap:.2f}s",
            })
            data["last_snap_time"] = 0  # prevent double-flagging
