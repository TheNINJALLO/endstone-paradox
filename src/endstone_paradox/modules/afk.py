# afk.py - Kick idle players after configurable timeout

import time
from endstone_paradox.modules.base import BaseModule


class AFKModule(BaseModule):
    """Detects and handles AFK (idle) players."""

    name = "afk"
    check_interval = 200  # Check every 10 seconds

    DEFAULT_TIMEOUT = 600  # 10 minutes in seconds

    def on_start(self):
        self._last_activity = {}  # UUID -> timestamp
        self._last_positions = {} # UUID -> (x, y, z)
        # Load timeout from config
        self._timeout = self.db.get("config", "afk_timeout", self.DEFAULT_TIMEOUT)
        # Initialize all online players
        now = time.time()
        for player in self.plugin.server.online_players:
            uuid_str = str(player.unique_id)
            self._last_activity[uuid_str] = now
            loc = player.location
            self._last_positions[uuid_str] = (loc.x, loc.y, loc.z)

    def on_stop(self):
        self._last_activity.clear()
        self._last_positions.clear()

    def on_player_leave(self, player):
        uuid_str = str(player.unique_id)
        self._last_activity.pop(uuid_str, None)
        self._last_positions.pop(uuid_str, None)

    def check(self):
        """Periodic check for idle players."""
        now = time.time()
        for player in self.plugin.server.online_players:
            try:
                uuid_str = str(player.unique_id)

                # Skip Level 4 players
                if self.plugin.security.is_level4(player):
                    self._last_activity[uuid_str] = now
                    continue

                loc = player.location
                current_pos = (loc.x, loc.y, loc.z)
                last_pos = self._last_positions.get(uuid_str)

                if last_pos:
                    # Check if player moved
                    dx = abs(current_pos[0] - last_pos[0])
                    dy = abs(current_pos[1] - last_pos[1])
                    dz = abs(current_pos[2] - last_pos[2])
                    if dx > 0.1 or dy > 0.1 or dz > 0.1:
                        self._last_activity[uuid_str] = now
                else:
                    self._last_activity[uuid_str] = now

                self._last_positions[uuid_str] = current_pos

                # Check timeout
                last = self._last_activity.get(uuid_str, now)
                idle_time = now - last
                if idle_time >= self._timeout:
                    player.kick(f"§eKicked for being AFK ({int(idle_time / 60)} minutes)")
                    self.alert_admins(
                        f"§7{player.name}§e kicked for AFK ({int(idle_time / 60)}min)"
                    )
                    self._last_activity.pop(uuid_str, None)
                    self._last_positions.pop(uuid_str, None)
                elif idle_time >= self._timeout - 60:
                    # Warning 1 minute before kick
                    remaining = int(self._timeout - idle_time)
                    player.send_message(
                        f"§2[§7Paradox§2]§e AFK Warning: You will be kicked in {remaining}s"
                    )
            except Exception:
                pass
