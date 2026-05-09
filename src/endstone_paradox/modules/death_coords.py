from endstone.event import PlayerDeathEvent
from endstone_paradox.modules.base import BaseModule

class DeathCoordsModule(BaseModule):
    """Sends a player their exact coordinates and dimension when they die."""

    name = "deathcoords"

    def on_player_death(self, event: PlayerDeathEvent):
        player = event.player
        if not player:
            return
            
        loc = player.location
        dim_name = player.dimension.name
        
        player.send_message(
            f"§cYou died at: §e{int(loc.x)}, {int(loc.y)}, {int(loc.z)} §cin §e{dim_name}"
        )
