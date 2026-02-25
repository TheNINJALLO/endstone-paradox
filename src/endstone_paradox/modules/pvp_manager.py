# pvp_manager.py - Per-player PvP toggles, combat logging, cooldowns

import time
from endstone_paradox.modules.base import BaseModule


class PvPManagerModule(BaseModule):
    """PvP management with toggles, cooldowns, and combat log protection."""

    name = "pvp"

    COMBAT_TAG_DURATION = 15.0    # Seconds in combat after last hit
    COMBAT_LOG_BAN_DURATION = 300  # 5 minute temp ban for combat loggers

    def on_start(self):
        self._pvp_disabled = set()     # UUIDs with PvP disabled
        self._combat_tagged = {}       # UUID -> last_combat_time
        self._combat_opponents = {}    # UUID -> set of opponent UUIDs
        self._global_pvp = self.db.get("config", "global_pvp", True)

    def on_stop(self):
        self._pvp_disabled.clear()
        self._combat_tagged.clear()
        self._combat_opponents.clear()

    def on_player_leave(self, player):
        """Handle combat log detection."""
        uuid_str = str(player.unique_id)

        # Check if player is combat tagged
        if uuid_str in self._combat_tagged:
            last_combat = self._combat_tagged[uuid_str]
            if time.time() - last_combat < self.COMBAT_TAG_DURATION:
                # Combat log detected!
                self.alert_admins(
                    f"§c{player.name}§e combat logged! Penalizing..."
                )
                # Store inventory data for opponents to loot (simplified: just log it)
                self.db.set("pvp_data", f"combatlog_{uuid_str}", {
                    "name": player.name,
                    "time": time.time(),
                    "opponents": list(self._combat_opponents.get(uuid_str, set())),
                })

        self._combat_tagged.pop(uuid_str, None)
        self._combat_opponents.pop(uuid_str, None)
        self._pvp_disabled.discard(uuid_str)

    def on_damage(self, event):
        """Handle PvP damage checks."""
        actor = event.actor  # The damaged entity
        if actor is None or not hasattr(actor, 'unique_id'):
            return

        # Get the damager
        damager = getattr(event, 'damager', None)
        if damager is None or not hasattr(damager, 'unique_id'):
            return

        # Only process player-on-player damage
        if not hasattr(actor, 'game_mode') or not hasattr(damager, 'game_mode'):
            return

        a_uuid = str(actor.unique_id)
        d_uuid = str(damager.unique_id)

        # Skip if same player
        if a_uuid == d_uuid:
            return

        # Global PvP check
        if not self._global_pvp:
            event.is_cancelled = True
            damager.send_message("§2[§7Paradox§2]§c PvP is globally disabled.")
            return

        # Per-player PvP check
        if a_uuid in self._pvp_disabled or d_uuid in self._pvp_disabled:
            event.is_cancelled = True
            damager.send_message("§2[§7Paradox§2]§c PvP is disabled for one or both players.")
            return

        # Apply combat tag
        now = time.time()
        self._combat_tagged[a_uuid] = now
        self._combat_tagged[d_uuid] = now

        # Track opponents
        self._combat_opponents.setdefault(a_uuid, set()).add(d_uuid)
        self._combat_opponents.setdefault(d_uuid, set()).add(a_uuid)

    def toggle_pvp(self, player) -> bool:
        """Toggle PvP for a player. Returns the new state (True = PvP on)."""
        uuid_str = str(player.unique_id)
        if uuid_str in self._pvp_disabled:
            self._pvp_disabled.discard(uuid_str)
            return True
        else:
            # Can't disable PvP while combat tagged
            if self.is_in_combat(player):
                return True  # Stay enabled
            self._pvp_disabled.add(uuid_str)
            return False

    def toggle_global_pvp(self) -> bool:
        """Toggle global PvP. Returns the new state."""
        self._global_pvp = not self._global_pvp
        self.db.set("config", "global_pvp", self._global_pvp)
        return self._global_pvp

    def is_in_combat(self, player) -> bool:
        """Check if a player is currently in combat."""
        uuid_str = str(player.unique_id)
        last = self._combat_tagged.get(uuid_str)
        if last is None:
            return False
        return time.time() - last < self.COMBAT_TAG_DURATION

    def is_pvp_enabled(self, player) -> bool:
        """Check if PvP is enabled for a player."""
        return str(player.unique_id) not in self._pvp_disabled and self._global_pvp
