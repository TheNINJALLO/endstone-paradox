# containersee.py - Container Vision admin tool
# Lets Level 4 admins see container contents by looking at them.
# Shows items in chat with auto-pagination — admin utility, not detection.

from endstone_paradox.modules.base import BaseModule


def _format_item_name(item_id: str) -> str:
    """Convert 'minecraft:diamond_sword' to 'Diamond Sword'."""
    name = item_id.replace("minecraft:", "")
    return " ".join(w.capitalize() for w in name.split("_"))


class ContainerSeeModule(BaseModule):
    """Admin tool: see container contents by looking at the container."""

    name = "containersee"
    check_interval = 30  # ~1.5 seconds

    ITEMS_PER_PAGE = 6
    ROTATE_EVERY = 3    # rotate page every 3 intervals
    MAX_DISTANCE = 10

    def on_start(self):
        self._page = {}       # uuid -> page index
        self._cooldown = {}   # uuid -> interval counter
        self._last_pos = {}   # uuid -> "x,y,z" of last viewed container

    def on_stop(self):
        self._page.clear()
        self._cooldown.clear()
        self._last_pos.clear()

    def on_player_leave(self, player):
        uid = str(player.unique_id)
        self._page.pop(uid, None)
        self._cooldown.pop(uid, None)
        self._last_pos.pop(uid, None)

    def check(self):
        """Run vision check on all Level 4 admins."""
        for player in self.plugin.server.online_players:
            try:
                if not self.plugin.security.is_level4(player):
                    continue
                self._check_player(player)
            except Exception:
                pass

    def _check_player(self, player):
        uid = str(player.unique_id)

        # Get the block the player is looking at
        try:
            target = player.get_target_block(self.MAX_DISTANCE)
        except Exception:
            target = None

        if target is None:
            self._cleanup(uid)
            return

        # Check if block has inventory
        container = self._get_container(target)
        if container is None:
            self._cleanup(uid)
            return

        # Detect container change → reset pagination
        pos_key = f"{target.x},{target.y},{target.z}"
        if self._last_pos.get(uid) != pos_key:
            self._last_pos[uid] = pos_key
            self._page[uid] = 0
            self._cooldown[uid] = 0

        # Count items
        counts = {}
        try:
            for i in range(container.size):
                item = container.get_item(i)
                if item is not None:
                    name = _format_item_name(str(item.type))
                    counts[name] = counts.get(name, 0) + item.amount
        except Exception:
            pass

        if not counts:
            player.send_message("§2[§7Paradox§2]§o§7 Container is empty")
            self._page[uid] = 0
            return

        # Paginate
        entries = list(counts.items())
        total_pages = max(1, -(-len(entries) // self.ITEMS_PER_PAGE))  # ceil div
        current_page = self._page.get(uid, 0) % total_pages
        start = current_page * self.ITEMS_PER_PAGE
        page_entries = entries[start:start + self.ITEMS_PER_PAGE]

        lines = []
        for name, amount in page_entries:
            lines.append(f"  §2[§f{name}§2]§7 x{amount}")

        header = "§2[§7Paradox§2]§a Container Contents:"
        if total_pages > 1:
            header += f" §8(Page {current_page + 1}/{total_pages})"

        player.send_message(header)
        for line in lines:
            player.send_message(line)

        # Auto-rotate pages
        cd = self._cooldown.get(uid, 0) + 1
        if cd >= self.ROTATE_EVERY:
            self._page[uid] = (current_page + 1) % total_pages
            self._cooldown[uid] = 0
        else:
            self._cooldown[uid] = cd

    def _get_container(self, block):
        """Try to get inventory from a block (chest, barrel, shulker, etc)."""
        try:
            inv = block.get_component("minecraft:inventory")
            if inv and hasattr(inv, 'container'):
                return inv.container
        except Exception:
            pass
        try:
            if hasattr(block, 'inventory'):
                return block.inventory
        except Exception:
            pass
        return None

    def _cleanup(self, uid):
        self._page.pop(uid, None)
        self._cooldown.pop(uid, None)
        self._last_pos.pop(uid, None)
