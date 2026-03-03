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
