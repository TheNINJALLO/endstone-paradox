"""
Paradox AntiCheat - Security Clearance System

Implements a 4-level security clearance hierarchy for command access control.
Uses SHA-256 password hashing (replacing Paradox's CryptoES).
"""

import hashlib
from enum import IntEnum
from typing import Optional, Set
from uuid import UUID


class SecurityClearance(IntEnum):
    """Security clearance levels for Paradox AntiCheat."""
    LEVEL_1 = 1  # Default - basic commands only
    LEVEL_2 = 2  # Moderate - utility commands
    LEVEL_3 = 3  # High - moderation commands
    LEVEL_4 = 4  # Maximum - full admin access, exempt from checks


def hash_password(password: str) -> str:
    """
    Hash a password using SHA-256.

    Args:
        password: The plaintext password to hash.

    Returns:
        The hex-encoded SHA-256 hash.
    """
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against a stored hash.

    Args:
        password: The plaintext password to verify.
        password_hash: The stored SHA-256 hash.

    Returns:
        True if the password matches.
    """
    return hash_password(password) == password_hash


class SecurityManager:
    """
    Manages security clearance levels for players.

    Tracks clearance levels in the database and maintains an in-memory
    set of Level 4 player UUIDs for fast lookup.
    """

    def __init__(self, db):
        """
        Initialize the security manager.

        Args:
            db: ParadoxDatabase instance.
        """
        self._db = db
        self._level4_players: Set[str] = set()
        self._load_level4_players()

    def _load_level4_players(self):
        """Load all Level 4 players from the database into memory."""
        self._level4_players.clear()
        all_players = self._db.get_all("players")
        for uuid_str, data in all_players.items():
            if isinstance(data, dict) and data.get("clearance") == SecurityClearance.LEVEL_4:
                self._level4_players.add(uuid_str)

    def get_clearance(self, player) -> SecurityClearance:
        """
        Get a player's security clearance level.

        Args:
            player: The Endstone Player object.

        Returns:
            The player's SecurityClearance level.
        """
        uuid_str = str(player.unique_id)
        data = self._db.get("players", uuid_str)
        if data and isinstance(data, dict):
            level = data.get("clearance", SecurityClearance.LEVEL_1)
            try:
                return SecurityClearance(level)
            except ValueError:
                return SecurityClearance.LEVEL_1
        return SecurityClearance.LEVEL_1

    def set_clearance(self, player, level: SecurityClearance):
        """
        Set a player's security clearance level.

        Args:
            player: The Endstone Player object.
            level: The SecurityClearance level to set.
        """
        uuid_str = str(player.unique_id)
        data = self._db.get("players", uuid_str, {})
        if not isinstance(data, dict):
            data = {}
        data["clearance"] = int(level)
        data["name"] = player.name
        self._db.set("players", uuid_str, data)

        # Update Level 4 tracker
        if level == SecurityClearance.LEVEL_4:
            self._level4_players.add(uuid_str)
        elif uuid_str in self._level4_players:
            self._level4_players.discard(uuid_str)

    def has_clearance(self, player, required: SecurityClearance) -> bool:
        """
        Check if a player has the required clearance level.

        Args:
            player: The Endstone Player object.
            required: The minimum SecurityClearance required.

        Returns:
            True if the player's clearance >= required.
        """
        return self.get_clearance(player) >= required

    def is_level4(self, player) -> bool:
        """Check if a player has Level 4 clearance (fast path via in-memory set)."""
        return str(player.unique_id) in self._level4_players

    def get_level4_players(self) -> Set[str]:
        """Get the set of all Level 4 player UUIDs."""
        return self._level4_players.copy()

    def get_stored_password_hash(self) -> Optional[str]:
        """Get the stored operator password hash."""
        return self._db.get("config", "op_password_hash")

    def set_password_hash(self, password_hash: str):
        """Store the operator password hash."""
        self._db.set("config", "op_password_hash", password_hash)

    def has_password_set(self) -> bool:
        """Check if an operator password has been set."""
        return self._db.has("config", "op_password_hash")
