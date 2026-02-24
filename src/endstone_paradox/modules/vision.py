"""
Paradox AntiCheat - Vision Detection Module

Detects look-direction anomalies that may indicate aimbots or
freecam exploits by tracking rapid yaw/pitch changes.
"""

import math
import time
from collections import deque
from endstone_paradox.modules.base import BaseModule


class VisionModule(BaseModule):
    """Detects vision anomalies (aimbot, freecam)."""

    name = "vision"
    check_interval = 5  # Check every 0.25 seconds

    MAX_ROTATION_SPEED = 180.0  # Degrees per tick (impossibly fast)
    SNAP_THRESHOLD = 90.0       # Sudden snap angle (degrees)
    SNAP_COUNT_LIMIT = 5        # Max snaps in window before flag
    WINDOW_SIZE = 2.0           # Analysis window (seconds)

    def on_start(self):
        self._rotation_data = {}  # UUID -> {last_yaw, last_pitch, snaps: deque}

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
                    self.alert_admins(
                        f"§c{player.name}§e flagged for suspicious aim "
                        f"({len(data['snaps'])} rapid snaps in {self.WINDOW_SIZE}s)"
                    )
                    data["snaps"].clear()
            except Exception:
                pass
