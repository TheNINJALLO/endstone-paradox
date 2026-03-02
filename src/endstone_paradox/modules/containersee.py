# containersee.py - Container & Player Vision admin tool
# Lets Level 4 admins see container contents by looking at containers,
# and player inventories by looking at players.
# Shows items in chat with auto-pagination — admin utility, not detection.

import math
from endstone_paradox.modules.base import BaseModule


def _format_item_name(item_id: str) -> str:
    """Convert 'minecraft:diamond_sword' to 'Diamond Sword'."""
    name = str(item_id).replace("minecraft:", "")
    return " ".join(w.capitalize() for w in name.split("_"))


class ContainerSeeModule(BaseModule):
    """Admin tool: see container/player inventory by looking at them."""

    name = "containersee"
    check_interval = 30  # ~1.5 seconds

    ITEMS_PER_PAGE = 6
    ROTATE_EVERY = 3    # rotate page every 3 intervals
    MAX_DISTANCE = 10
    PLAYER_ANGLE = 15.0  # degrees — how closely admin must be looking at player

    def on_start(self):
        self._page = {}       # uuid -> page index
        self._cooldown = {}   # uuid -> interval counter
        self._last_target = {}  # uuid -> "block:x,y,z" or "player:uuid" key

    def on_stop(self):
        self._page.clear()
        self._cooldown.clear()
        self._last_target.clear()

    def on_player_leave(self, player):
        uid = str(player.unique_id)
        self._page.pop(uid, None)
        self._cooldown.pop(uid, None)
        self._last_target.pop(uid, None)

    def check(self):
        """Run vision check on all Level 4 admins."""
        for player in self.plugin.server.online_players:
            try:
                if not self.plugin.security.is_level4(player):
                    continue
                self._check_player(player)
            except Exception:
                pass

    def _check_player(self, admin):
        uid = str(admin.unique_id)

        # Priority 1: Check if looking at a player
        target_player = self._find_target_player(admin)
        if target_player is not None:
            target_key = f"player:{target_player.unique_id}"
            if self._last_target.get(uid) != target_key:
                self._last_target[uid] = target_key
                self._page[uid] = 0
                self._cooldown[uid] = 0
            self._show_player_inventory(admin, target_player, uid)
            return

        # Priority 2: Check if looking at a container block
        try:
            target_block = admin.get_target_block(self.MAX_DISTANCE)
        except Exception:
            target_block = None

        if target_block is not None:
            container = self._get_container(target_block)
            if container is not None:
                target_key = f"block:{target_block.x},{target_block.y},{target_block.z}"
                if self._last_target.get(uid) != target_key:
                    self._last_target[uid] = target_key
                    self._page[uid] = 0
                    self._cooldown[uid] = 0
                self._show_container(admin, container, uid)
                return

        # Nothing found — cleanup
        self._cleanup(uid)

    # ─── Player Inventory ────────────────────────────────

    def _find_target_player(self, admin):
        """Find the player the admin is looking at (within angle threshold)."""
        try:
            a_loc = admin.location
            a_rot = admin.rotation  # (pitch, yaw)

            # Build view direction from yaw and pitch
            yaw_rad = math.radians(a_rot.y if hasattr(a_rot, 'y') else 0)
            pitch_rad = math.radians(a_rot.x if hasattr(a_rot, 'x') else 0)

            # Minecraft: yaw=0 is south (+Z), increases clockwise
            view_x = -math.sin(yaw_rad) * math.cos(pitch_rad)
            view_y = -math.sin(pitch_rad)
            view_z = math.cos(yaw_rad) * math.cos(pitch_rad)

            view_len = math.sqrt(view_x**2 + view_y**2 + view_z**2)
            if view_len < 0.001:
                return None
            view_x /= view_len
            view_y /= view_len
            view_z /= view_len

            best_player = None
            best_angle = self.PLAYER_ANGLE

            eye_y = a_loc.y + 1.62  # eye height

            for other in self.plugin.server.online_players:
                if other.unique_id == admin.unique_id:
                    continue

                o_loc = other.location
                dx = o_loc.x - a_loc.x
                dy = (o_loc.y + 0.9) - eye_y  # target body center
                dz = o_loc.z - a_loc.z
                dist = math.sqrt(dx*dx + dy*dy + dz*dz)

                if dist < 1.0 or dist > self.MAX_DISTANCE:
                    continue

                # Normalize direction to other player
                dx /= dist
                dy /= dist
                dz /= dist

                # Dot product for angle
                dot = view_x * dx + view_y * dy + view_z * dz
                dot = max(-1.0, min(1.0, dot))  # clamp
                angle = math.degrees(math.acos(dot))

                if angle < best_angle:
                    best_angle = angle
                    best_player = other

            return best_player

        except Exception:
            return None

    def _show_player_inventory(self, admin, target, uid):
        """Show target player's inventory to admin."""
        counts = {}
        armor_items = []

        try:
            inv = target.inventory
            if inv is not None:
                # Main inventory
                for i in range(inv.size):
                    try:
                        item = inv.get_item(i)
                        if item is not None:
                            name = _format_item_name(str(item.type))
                            counts[name] = counts.get(name, 0) + item.amount
                    except Exception:
                        pass
        except Exception:
            pass

        # Try to get armor
        try:
            armor = target.inventory
            if armor and hasattr(armor, 'helmet'):
                for slot_name in ['helmet', 'chestplate', 'leggings', 'boots']:
                    try:
                        piece = getattr(armor, slot_name, None)
                        if piece is not None:
                            armor_items.append(
                                f"§3{slot_name.capitalize()}§7: §f{_format_item_name(str(piece.type))}"
                            )
                    except Exception:
                        pass
        except Exception:
            pass

        # Build display
        if not counts and not armor_items:
            admin.send_message(
                f"§2[§7Paradox§2]§7 {target.name}'s inventory is empty"
            )
            self._page[uid] = 0
            return

        # Paginate items
        entries = list(counts.items())
        total_pages = max(1, -(-len(entries) // self.ITEMS_PER_PAGE)) if entries else 1
        current_page = self._page.get(uid, 0) % total_pages
        start = current_page * self.ITEMS_PER_PAGE
        page_entries = entries[start:start + self.ITEMS_PER_PAGE]

        admin.send_message(
            f"§2[§7Paradox§2]§b {target.name}§a's Inventory:"
            + (f" §8(Page {current_page + 1}/{total_pages})" if total_pages > 1 else "")
        )

        # Show armor on first page
        if current_page == 0 and armor_items:
            admin.send_message("  §3Armor:")
            for a in armor_items:
                admin.send_message(f"    {a}")

        for item_name, amount in page_entries:
            admin.send_message(f"  §2[§f{item_name}§2]§7 x{amount}")

        # Auto-rotate
        cd = self._cooldown.get(uid, 0) + 1
        if cd >= self.ROTATE_EVERY:
            self._page[uid] = (current_page + 1) % total_pages
            self._cooldown[uid] = 0
        else:
            self._cooldown[uid] = cd

    # ─── Container Contents ──────────────────────────────

    def _show_container(self, admin, container, uid):
        """Show container contents to admin."""
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
            admin.send_message("§2[§7Paradox§2]§o§7 Container is empty")
            self._page[uid] = 0
            return

        entries = list(counts.items())
        total_pages = max(1, -(-len(entries) // self.ITEMS_PER_PAGE))
        current_page = self._page.get(uid, 0) % total_pages
        start = current_page * self.ITEMS_PER_PAGE
        page_entries = entries[start:start + self.ITEMS_PER_PAGE]

        header = "§2[§7Paradox§2]§a Container Contents:"
        if total_pages > 1:
            header += f" §8(Page {current_page + 1}/{total_pages})"

        admin.send_message(header)
        for name, amount in page_entries:
            admin.send_message(f"  §2[§f{name}§2]§7 x{amount}")

        cd = self._cooldown.get(uid, 0) + 1
        if cd >= self.ROTATE_EVERY:
            self._page[uid] = (current_page + 1) % total_pages
            self._cooldown[uid] = 0
        else:
            self._cooldown[uid] = cd

    # ─── Utilities ───────────────────────────────────────

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
        self._last_target.pop(uid, None)
