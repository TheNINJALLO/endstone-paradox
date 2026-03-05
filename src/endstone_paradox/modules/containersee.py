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
        """Run vision check on all OP or Level 4 admins."""
        try:
            for player in self.plugin.server.online_players:
                try:
                    if not self.plugin.security.is_level4(player) and not getattr(player, 'is_op', False):
                        continue
                    self._check_player(player)
                except Exception:
                    pass
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
        target_block = None
        try:
            target_block = self._raycast_block(admin)
        except Exception:
            pass

        if target_block is not None:
            block_type = str(target_block.type).lower()
            # Only process known container block types
            if self._is_container_type(block_type):
                bx, by, bz = target_block.x, target_block.y, target_block.z
                target_key = f"block:{bx},{by},{bz}"
                if self._last_target.get(uid) != target_key:
                    self._last_target[uid] = target_key
                    self._page[uid] = 0
                    self._cooldown[uid] = 0
                self._show_container_via_command(admin, bx, by, bz, uid)
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
            try:
                admin.send_tip(f"§2[Paradox]§7 {target.name}'s inventory is empty")
            except Exception:
                admin.send_message(f"§2[Paradox]§7 {target.name}'s inventory is empty")
            self._page[uid] = 0
            return

        # Paginate items
        entries = list(counts.items())
        total_pages = max(1, -(-len(entries) // self.ITEMS_PER_PAGE)) if entries else 1
        current_page = self._page.get(uid, 0) % total_pages
        start = current_page * self.ITEMS_PER_PAGE
        page_entries = entries[start:start + self.ITEMS_PER_PAGE]

        lines = []
        header = f"§2[Paradox]§b {target.name}§a's Inventory:"
        if total_pages > 1:
            header += f" §8({current_page + 1}/{total_pages})"
        lines.append(header)

        # Show armor on first page
        if current_page == 0 and armor_items:
            for a in armor_items:
                lines.append(f"  {a}")

        for item_name, amount in page_entries:
            lines.append(f"  §f{item_name}§7 x{amount}")

        try:
            admin.send_tip("\n".join(lines))
        except Exception:
            for line in lines:
                admin.send_message(line)

        # Auto-rotate
        cd = self._cooldown.get(uid, 0) + 1
        if cd >= self.ROTATE_EVERY:
            self._page[uid] = (current_page + 1) % total_pages
            self._cooldown[uid] = 0
        else:
            self._cooldown[uid] = cd

    # ─── Container Contents ──────────────────────────────

    CONTAINER_TYPES = {
        "chest", "trapped_chest", "barrel", "shulker_box",
        "white_shulker_box", "orange_shulker_box", "magenta_shulker_box",
        "light_blue_shulker_box", "yellow_shulker_box", "lime_shulker_box",
        "pink_shulker_box", "gray_shulker_box", "silver_shulker_box",
        "light_gray_shulker_box", "cyan_shulker_box", "purple_shulker_box",
        "blue_shulker_box", "brown_shulker_box", "green_shulker_box",
        "red_shulker_box", "black_shulker_box",
        "hopper", "dispenser", "dropper", "furnace", "blast_furnace",
        "smoker", "brewing_stand", "undyed_shulker_box",
    }

    def _is_container_type(self, block_type: str) -> bool:
        """Check if a block type is a known container."""
        # Strip minecraft: prefix
        short = block_type.replace("minecraft:", "")
        return short in self.CONTAINER_TYPES

    def _show_container_via_command(self, admin, bx, by, bz, uid):
        """Show container identification to admin via action bar tip.

        Note: Endstone's Block API doesn't expose container inventories.
        This identifies the container type; player inventory vision (Priority 1)
        uses player.inventory which IS available.
        """
        try:
            block = admin.dimension.get_block_at(bx, by, bz)
            if block is None:
                return
            block_type = str(block.type).replace("minecraft:", "")
            block_name = _format_item_name(f"minecraft:{block_type}")
            try:
                admin.send_tip(f"§2[Paradox]§7 Container: §f{block_name}")
            except Exception:
                admin.send_message(f"§2[Paradox]§7 Container: {block_name}")
        except Exception:
            pass

    # ─── Utilities ───────────────────────────────────────

    def _raycast_block(self, player):
        """Manual raycast: step along view direction to find the first non-air block."""
        loc = player.location
        ex, ey, ez = loc.x, loc.y + 1.62, loc.z

        yaw_rad = math.radians(loc.yaw)
        pitch_rad = math.radians(loc.pitch)

        dx = -math.sin(yaw_rad) * math.cos(pitch_rad)
        dy = -math.sin(pitch_rad)
        dz = math.cos(yaw_rad) * math.cos(pitch_rad)

        step = 0.5
        dim = player.dimension
        prev_bx, prev_by, prev_bz = None, None, None

        for i in range(int(self.MAX_DISTANCE / step) + 1):
            cx = ex + dx * step * i
            cy = ey + dy * step * i
            cz = ez + dz * step * i

            bx = int(cx) if cx >= 0 else int(cx) - 1
            by = int(cy)
            bz = int(cz) if cz >= 0 else int(cz) - 1

            if (bx, by, bz) == (prev_bx, prev_by, prev_bz):
                continue
            prev_bx, prev_by, prev_bz = bx, by, bz

            try:
                block = dim.get_block_at(bx, by, bz)
                if block is not None:
                    block_type = str(block.type).lower()
                    if "air" not in block_type:
                        return block
            except Exception:
                pass

        return None

    def _cleanup(self, uid):
        self._page.pop(uid, None)
        self._cooldown.pop(uid, None)
        self._last_target.pop(uid, None)
