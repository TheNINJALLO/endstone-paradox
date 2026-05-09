from endstone.event import PlayerTeleportEvent
from endstone_paradox.modules.base import BaseModule

class DimensionLockModule(BaseModule):
    """Restricts access to specific dimensions (Nether/The End)."""

    name = "dimensionlock"

    def on_player_teleport(self, event: PlayerTeleportEvent):
        if getattr(event, 'is_cancelled', False):
            return

        player = event.player
        if not player:
            return

        # Exempt Level 4 admins
        if self.plugin.security.is_level4(player):
            return

        to_loc = event.to
        if not to_loc:
            return

        to_dim = to_loc.dimension.name.lower()
        
        # Load locked dimensions from database or config (default to empty list if none set)
        # Using a list in the DB under 'settings', 'locked_dimensions'
        locked_dims = self.db.get("settings", "locked_dimensions", [])
        
        # Convert all locked dimensions to lower case for comparison
        locked_dims_lower = [d.lower() for d in locked_dims]

        # Dimension names usually like 'nether', 'the end', 'overworld'
        # In Endstone, dimension.type might be Dimension.Type.NETHER etc., but dimension.name is string
        if to_dim in locked_dims_lower or any(d in to_dim for d in locked_dims_lower):
            event.is_cancelled = True
            player.send_message(f"§cAccess to the {to_loc.dimension.name} is currently locked by administrators.")
            
            # Emit a low-level violation/log
            self.emit(player, 0, {
                "type": "dimension_lock",
                "desc": f"Attempted to access locked dimension: {to_loc.dimension.name}"
            })
