# namespoof.py - Name validation (length, chars, duplicates)

import re
import time
from endstone_paradox.modules.base import BaseModule


class NameSpoofModule(BaseModule):
    """Detects namespoofing via name validation rules."""

    name = "namespoof"

    # Name validation rules
    MIN_NAME_LENGTH = 3
    MAX_NAME_LENGTH = 16
    ALLOWED_PATTERN = re.compile(r'^[A-Za-z0-9_ ]+$')

    def on_start(self):
        self._known_names = {}  # name_lower -> UUID (for duplicate detection)
        # Load existing players
        for player in self.plugin.server.online_players:
            self._known_names[player.name.lower()] = str(player.unique_id)

    def on_stop(self):
        self._known_names.clear()

    def on_player_leave(self, player):
        name_lower = player.name.lower()
        uuid_str = str(player.unique_id)
        if self._known_names.get(name_lower) == uuid_str:
            self._known_names.pop(name_lower, None)

    def check_player(self, player) -> bool:
        """
        Validate a player's name on join.

        Returns True if the name is valid, False if it should be rejected.
        Called from the player join handler.
        """
        name = player.name
        uuid_str = str(player.unique_id)

        # Length check
        if len(name) < self.MIN_NAME_LENGTH or len(name) > self.MAX_NAME_LENGTH:
            self._log_spoof(player, f"Invalid name length: {len(name)}")
            player.kick("§cInvalid name length.")
            self.alert_admins(
                f"§c{name}§e kicked for invalid name length ({len(name)} chars)"
            )
            return False

        # Character check
        if not self.ALLOWED_PATTERN.match(name):
            self._log_spoof(player, f"Invalid characters in name: {name}")
            player.kick("§cInvalid characters in name.")
            self.alert_admins(
                f"§c{name}§e kicked for invalid characters in name"
            )
            return False

        # Duplicate check
        name_lower = name.lower()
        existing_uuid = self._known_names.get(name_lower)
        if existing_uuid and existing_uuid != uuid_str:
            self._log_spoof(player, f"Duplicate name: {name}")
            player.kick("§cDuplicate name detected.")
            self.alert_admins(
                f"§c{name}§e kicked for duplicate name (spoofing?)"
            )
            return False

        # Register the name
        self._known_names[name_lower] = uuid_str
        return True

    def _log_spoof(self, player, reason: str):
        """Log a namespoof event to the database."""
        entry = {
            "name": player.name,
            "uuid": str(player.unique_id),
            "reason": reason,
            "time": time.time(),
        }
        # Store as sequential log entries
        count = self.db.count("spoof_log")
        self.db.set("spoof_log", str(count + 1), entry)
