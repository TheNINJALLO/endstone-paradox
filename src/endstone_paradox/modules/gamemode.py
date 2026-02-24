"""
Paradox AntiCheat - GameMode Detection Module

Detects unauthorized gamemode changes for non-admin players.
"""

from endstone import GameMode
from endstone_paradox.modules.base import BaseModule


class GameModeModule(BaseModule):
    """Detects unauthorized gamemode changes."""

    name = "gamemode"

    ALLOWED_MODES = {GameMode.SURVIVAL, GameMode.ADVENTURE}

    def on_start(self):
        pass

    def on_gamemode_change(self, event):
        """Monitor gamemode changes."""
        player = event.player
        if player is None:
            return
        if self.plugin.security.is_level4(player):
            return

        new_mode = event.new_game_mode
        if new_mode not in self.ALLOWED_MODES:
            event.is_cancelled = True
            self.alert_admins(
                f"§c{player.name}§e attempted unauthorized gamemode change to {new_mode.name}"
            )
