# illegal_items.py - Illegal Item Scanner
# Detects and removes items with illegal enchantments, stack sizes, or creative-only presence.

import time
from endstone import GameMode
from endstone_paradox.modules.base import BaseModule


class IllegalItemsModule(BaseModule):
    """Scans player inventories for illegal items.

    Detects:
    - Enchantments above vanilla max (e.g. Sharpness > 5)
    - Stack sizes above vanilla max (e.g. 64+ swords)
    - Creative-only items in survival mode (e.g. bedrock, command blocks)

    Runs periodically and on player join.
    """

    name = "illegalitems"
    check_interval = 600  # every 30 seconds

    # Maximum enchantment levels (vanilla)
    MAX_ENCHANT_LEVELS = {
        "sharpness": 5, "smite": 5, "bane_of_arthropods": 5,
        "knockback": 2, "fire_aspect": 2, "looting": 3,
        "sweeping": 3, "sweeping_edge": 3,
        "efficiency": 5, "silk_touch": 1, "unbreaking": 3,
        "fortune": 3,
        "power": 5, "punch": 2, "flame": 1, "infinity": 1,
        "protection": 4, "fire_protection": 4,
        "blast_protection": 4, "projectile_protection": 4,
        "thorns": 3,
        "respiration": 3, "depth_strider": 3,
        "aqua_affinity": 1, "feather_falling": 4,
        "frost_walker": 2,
        "soul_speed": 3, "swift_sneak": 3,
        "mending": 1,
        "curse_of_vanishing": 1, "curse_of_binding": 1,
        "loyalty": 3, "impaling": 5, "riptide": 3, "channeling": 1,
        "multishot": 1, "quick_charge": 3, "piercing": 4,
        "density": 5, "breach": 4, "wind_burst": 3,
    }

    # Items that should never exist in survival
    CREATIVE_ONLY = {
        "bedrock", "command_block", "chain_command_block",
        "repeating_command_block", "structure_block", "structure_void",
        "jigsaw", "barrier", "light", "light_block",
        "debug_stick", "knowledge_book",
        "command_block_minecart",
        "spawn_egg",  # all spawn eggs (will match via 'in')
        "allow", "deny", "border_block",
    }

    # Max stack sizes (non-standard items)
    UNSTACKABLE = {
        "sword", "pickaxe", "axe", "shovel", "hoe",
        "bow", "crossbow", "trident", "mace",
        "helmet", "chestplate", "leggings", "boots",
        "shield", "elytra", "fishing_rod",
        "shears", "flint_and_steel",
        "totem", "enchanted_book", "potion",
        "splash_potion", "lingering_potion",
        "bucket", "lava_bucket", "water_bucket",
        "bed", "boat", "minecart",
    }

    def on_start(self):
        self._last_scan = {}  # uuid -> timestamp
        self._apply_sensitivity()

    def _apply_sensitivity(self):
        pass  # no sensitivity scaling for item scanner

    def on_stop(self):
        self._last_scan.clear()

    def on_player_leave(self, player):
        self._last_scan.pop(str(player.unique_id), None)

    def on_player_join(self, player):
        """Scan on join after a short delay."""
        uuid_str = str(player.unique_id)
        self._last_scan[uuid_str] = 0  # force scan on next check

    def check(self):
        """Periodic inventory scan."""
        now = time.time()
        for player in self.plugin.server.online_players:
            try:
                uuid_str = str(player.unique_id)
                if self.plugin.security.is_level4(player):
                    continue

                # Don't scan creative players
                if player.game_mode == GameMode.CREATIVE:
                    continue

                # Rate limit scans per player
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

            # Check each slot
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
                                "item": item_type,
                                "reason": "creative_only",
                                "slot": slot_idx,
                            }, action_hint="cancel")
                            try:
                                inventory.set_item(slot_idx, None)
                            except Exception:
                                pass
                            return  # one flag per scan

                    # Stack size check
                    if hasattr(item, 'amount') and item.amount > 1:
                        for unstackable in self.UNSTACKABLE:
                            if unstackable in item_type:
                                self.emit(player, 4, {
                                    "type": "illegal_stack",
                                    "item": item_type,
                                    "amount": item.amount,
                                    "slot": slot_idx,
                                }, action_hint="cancel")
                                try:
                                    inventory.set_item(slot_idx, None)
                                except Exception:
                                    pass
                                return

                    # Enchantment level check
                    enchants = None
                    if hasattr(item, 'enchantments'):
                        enchants = item.enchantments
                    elif hasattr(item, 'get_enchantments'):
                        enchants = item.get_enchantments()

                    if enchants:
                        try:
                            for ench in enchants:
                                ench_name = str(ench.type if hasattr(ench, 'type') else ench).lower().replace("minecraft:", "")
                                ench_level = ench.level if hasattr(ench, 'level') else 0
                                max_level = self.MAX_ENCHANT_LEVELS.get(ench_name, 5)

                                if ench_level > max_level:
                                    self.emit(player, 4, {
                                        "type": "illegal_enchant",
                                        "item": item_type,
                                        "enchant": ench_name,
                                        "level": ench_level,
                                        "max": max_level,
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
