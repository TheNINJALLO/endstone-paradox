# lag_clear.py - Periodic ground item cleanup

import time
from endstone_paradox.modules.base import BaseModule


class LagClearModule(BaseModule):
    """Scheduled entity cleanup for lag reduction."""

    name = "lagclear"

    DEFAULT_INTERVAL = 300  # 5 minutes in seconds (6000 ticks)

    def on_start(self):
        self._interval = self.db.get("config", "lagclear_interval", self.DEFAULT_INTERVAL)
        self._last_clear = time.time()
        self._warning_sent = False

    @property
    def check_interval(self) -> int:
        return 200  # Check every 10 seconds

    def check(self):
        """Check if it's time for a lag clear."""
        now = time.time()
        elapsed = now - self._last_clear

        # Send warning 30 seconds before clear
        if elapsed >= self._interval - 30 and not self._warning_sent:
            self._warning_sent = True
            for player in self.plugin.server.online_players:
                player.send_message(
                    "§2[§7Paradox§2]§e Ground items will be cleared in 30 seconds!"
                )

        if elapsed >= self._interval:
            self._perform_clear()
            self._last_clear = now
            self._warning_sent = False

    def _perform_clear(self):
        """Remove ground items from all dimensions."""
        removed = 0
        try:
            for player in self.plugin.server.online_players:
                dim = player.dimension
                # Get entities near the player (items on ground)
                # Endstone doesn't have a direct "get all entities" API easily,
                # so we use the server command approach
                break  # Only need one player to get server reference

            # Use the /kill command to remove items
            self.plugin.server.dispatch_command(
                self.plugin.server.command_sender,
                "kill @e[type=item]"
            )
            removed = -1  # Can't get count from command

            for player in self.plugin.server.online_players:
                player.send_message(
                    "§2[§7Paradox§2]§a Ground items have been cleared!"
                )
        except Exception as e:
            self.logger.error(f"Lag clear error: {e}")

    def set_interval(self, seconds: int):
        """Update the lag clear interval."""
        self._interval = max(60, seconds)  # Minimum 1 minute
        self.db.set("config", "lagclear_interval", self._interval)

    def force_clear(self):
        """Force an immediate lag clear."""
        self._perform_clear()
        self._last_clear = time.time()
        self._warning_sent = False
