# illegal_items.py - Illegal Item Scanner
# Detects and removes items with illegal enchantments or creative-only items.

import time
from endstone import GameMode
from endstone_paradox.modules.base import BaseModule


class IllegalItemsModule(BaseModule):
    """Scans player inventories for illegal items.

    Detects:
    - Enchantments above configurable max level (default 10)
    - Creative-only items in survival mode (e.g. bedrock, command blocks)

    Max enchant level is configurable via web UI or DB config.
    Runs periodically and on player join.
    """

    name = "illegalitems"
    check_interval = 600  # every 30 seconds

    DEFAULT_MAX_ENCHANT = 10  # global max enchant level (configurable)

    # Items that should never exist in survival
    # NOTE: These are matched via substring — be VERY specific to avoid
    # false positives (e.g. "light" would match "froglight").
    CREATIVE_ONLY = {
        "bedrock", "command_block", "chain_command_block",
        "repeating_command_block", "structure_block", "structure_void",
        "jigsaw", "barrier", "light_block",
        "debug_stick", "knowledge_book",
        "command_block_minecart",
        "border_block",
    }

    # Only dangerous/hostile spawn eggs are banned — passive mob eggs are allowed
    BANNED_SPAWN_EGGS = {
        "wither_spawn_egg", "ender_dragon_spawn_egg",
        "elder_guardian_spawn_egg", "warden_spawn_egg",
        "agent_spawn_egg",
    }

    def on_start(self):
        self._last_scan = {}
        # Load configurable max enchant level from DB
        stored = self.db.get("config", "max_enchant_level")
        if stored is not None:
            self._max_enchant = max(1, int(stored))
        else:
            self._max_enchant = self.DEFAULT_MAX_ENCHANT
        self._apply_sensitivity()

    @property
    def max_enchant_level(self):
        return self._max_enchant

    @max_enchant_level.setter
    def max_enchant_level(self, value):
        self._max_enchant = max(1, int(value))
        self.db.set("config", "max_enchant_level", self._max_enchant)

    def _apply_sensitivity(self):
        pass

    def on_stop(self):
        self._last_scan.clear()

    def on_player_leave(self, player):
        self._last_scan.pop(str(player.unique_id), None)

    def on_player_join(self, player):
        """Scan on join after a short delay."""
        self._last_scan[str(player.unique_id)] = 0

    def check(self):
        """Periodic inventory scan."""
        now = time.time()
        for player in self.plugin.server.online_players:
            try:
                uuid_str = str(player.unique_id)
                if self.plugin.security.is_level4(player):
                    continue
                if player.game_mode == GameMode.CREATIVE:
                    continue
                last = self._last_scan.get(uuid_str, 0)
                if now - last < 30:
                    continue
                self._last_scan[uuid_str] = now
                self._scan_player(player)
            except Exception:
                pass

    def _scan_player(self, player):
        """Scan a player's inventory for illegal items."""
        try:
            inventory = player.inventory
            if inventory is None:
                return

            for slot_idx in range(inventory.size):
                try:
                    item = inventory.get_item(slot_idx)
                    if item is None:
                        continue

                    item_type = str(item.type).lower().replace("minecraft:", "")

                    # Creative-only items in survival
                    for creative_item in self.CREATIVE_ONLY:
                        if creative_item in item_type:
                            self.emit(player, 5, {
                                "type": "illegal_item",
                                "desc": f"Had creative-only item '{item_type}' in slot {slot_idx}",
                                "item": item_type,
                                "reason": "creative_only",
                                "slot": slot_idx,
                            }, action_hint="cancel")
                            try:
                                inventory.set_item(slot_idx, None)
                            except Exception:
                                pass
                            return

                    # Banned spawn eggs (exact match — passive mob eggs allowed)
                    if item_type in self.BANNED_SPAWN_EGGS:
                        self.emit(player, 5, {
                            "type": "illegal_item",
                            "desc": f"Had banned spawn egg '{item_type}' in slot {slot_idx}",
                            "item": item_type,
                            "reason": "banned_spawn_egg",
                            "slot": slot_idx,
                        }, action_hint="cancel")
                        try:
                            inventory.set_item(slot_idx, None)
                        except Exception:
                            pass
                        return

                    # Enchantment level check (uses configurable global max)
                    enchants = None
                    if hasattr(item, 'enchantments'):
                        enchants = item.enchantments
                    elif hasattr(item, 'get_enchantments'):
                        enchants = item.get_enchantments()

                    if enchants:
                        try:
                            for ench in enchants:
                                ench_name = str(
                                    ench.type if hasattr(ench, 'type') else ench
                                ).lower().replace("minecraft:", "")
                                ench_level = ench.level if hasattr(ench, 'level') else 0

                                if ench_level > self._max_enchant:
                                    self.emit(player, 4, {
                                        "type": "illegal_enchant",
                                        "desc": f"Item '{item_type}' has {ench_name} level {ench_level} (max {self._max_enchant})",
                                        "item": item_type,
                                        "enchant": ench_name,
                                        "level": ench_level,
                                        "max": self._max_enchant,
                                        "slot": slot_idx,
                                    }, action_hint="cancel")
                                    try:
                                        inventory.set_item(slot_idx, None)
                                    except Exception:
                                        pass
                                    return
                        except Exception:
                            pass

                except Exception:
                    pass
        except Exception:
            pass
