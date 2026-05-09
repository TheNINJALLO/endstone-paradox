import time
from endstone.event import PlayerInteractEvent, BlockBreakEvent, BlockPlaceEvent
from endstone_paradox.modules.base import BaseModule

class ContainerLockModule(BaseModule):
    """Allows players to lock their chests/barrels/shulkers using a stick."""

    name = "containerlock"
    
    LOCKABLE_BLOCKS = {
        "chest", "trapped_chest", "barrel", "shulker_box",
        "white_shulker_box", "orange_shulker_box", "magenta_shulker_box",
        "light_blue_shulker_box", "yellow_shulker_box", "lime_shulker_box",
        "pink_shulker_box", "gray_shulker_box", "silver_shulker_box",
        "light_gray_shulker_box", "cyan_shulker_box", "purple_shulker_box",
        "blue_shulker_box", "brown_shulker_box", "green_shulker_box",
        "red_shulker_box", "black_shulker_box",
    }

    def _is_container(self, block_type: str) -> bool:
        short = block_type.replace("minecraft:", "")
        return short in self.LOCKABLE_BLOCKS

    def _get_key(self, block):
        # We also need to handle double chests by normalizing to the primary block.
        # But for simplicity, we use dimension and coords.
        return f"{block.dimension.name}:{block.x},{block.y},{block.z}"

    def on_player_interact(self, event: PlayerInteractEvent):
        if getattr(event, 'is_cancelled', False):
            return

        block = event.block
        if not block:
            return

        block_type = str(block.type).lower()
        if not self._is_container(block_type):
            return

        player = event.player
        uid = str(player.unique_id)
        key = self._get_key(block)
        
        lock_data = self.db.get("chestLockDB", key)
        
        # Check if they are trying to lock/unlock with a stick
        item = player.inventory.item_in_hand if player.inventory else None
        if item and "stick" in str(item.type).lower():
            if not lock_data:
                # Lock it
                self.db.set("chestLockDB", key, {
                    "owner": uid,
                    "owner_name": player.name,
                    "timestamp": time.time()
                })
                player.send_message("§aContainer locked successfully!")
                event.is_cancelled = True
                return
            else:
                # Check if owner
                if lock_data.get("owner") == uid or self.plugin.security.is_level4(player):
                    self.db.delete("chestLockDB", key)
                    player.send_message("§eContainer unlocked.")
                else:
                    player.send_message(f"§cThis container is locked by {lock_data.get('owner_name')}.")
                event.is_cancelled = True
                return

        # Normal interaction (opening)
        if lock_data:
            if lock_data.get("owner") != uid and not self.plugin.security.is_level4(player):
                player.send_message(f"§cThis container is locked by {lock_data.get('owner_name')}.")
                event.is_cancelled = True
                
                # Emit violation for attempting to open locked chest
                self.emit(player, 1, {
                    "type": "locked_container_access",
                    "desc": f"Attempted to access locked container owned by {lock_data.get('owner_name')}"
                })

    def on_block_break(self, event: BlockBreakEvent):
        if getattr(event, 'is_cancelled', False):
            return

        block = event.block
        block_type = str(block.type).lower()
        if not self._is_container(block_type):
            return

        key = self._get_key(block)
        lock_data = self.db.get("chestLockDB", key)
        if lock_data:
            player = event.player
            uid = str(player.unique_id)
            if lock_data.get("owner") != uid and not self.plugin.security.is_level4(player):
                player.send_message(f"§cYou cannot break a container locked by {lock_data.get('owner_name')}.")
                event.is_cancelled = True
            else:
                # Owner breaking it, remove lock
                self.db.delete("chestLockDB", key)

    def on_block_place(self, event: BlockPlaceEvent):
        pass # In a complete implementation, placing a chest next to a locked chest might be blocked or automatically locked
