# gamemode.py - Blocks unauthorized gamemode changes

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
            self.emit(player, 4, {
                "mode": new_mode.name,
            }, action_hint="cancel")
