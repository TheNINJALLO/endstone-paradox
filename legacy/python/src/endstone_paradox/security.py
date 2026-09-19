# security.py - 4-level clearance system
# Replaces the original Paradox CryptoES setup with SHA-256 hashing.

import hashlib
from enum import IntEnum
from typing import Optional, Set
from uuid import UUID


class SecurityClearance(IntEnum):
    LEVEL_1 = 1  # default, basic commands
    LEVEL_2 = 2  # moderate, utility
    LEVEL_3 = 3  # high, moderation
    LEVEL_4 = 4  # full admin, exempt from all checks


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash


class SecurityManager:
    """Tracks player clearance levels. L4 players are cached in-memory for speed."""

    def __init__(self, db):
        self._db = db
        self._level4_players: Set[str] = set()
        self._load_level4_players()

    def _load_level4_players(self):
        self._level4_players.clear()
        all_players = self._db.get_all("players")
        for uuid_str, data in all_players.items():
            if isinstance(data, dict) and data.get("clearance") == SecurityClearance.LEVEL_4:
                self._level4_players.add(uuid_str)

    def get_clearance(self, player) -> SecurityClearance:
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
        uuid_str = str(player.unique_id)
        data = self._db.get("players", uuid_str, {})
        if not isinstance(data, dict):
            data = {}
        data["clearance"] = int(level)
        data["name"] = player.name
        self._db.set("players", uuid_str, data)

        # keep L4 cache in sync
        if level == SecurityClearance.LEVEL_4:
            self._level4_players.add(uuid_str)
        elif uuid_str in self._level4_players:
            self._level4_players.discard(uuid_str)

    def has_clearance(self, player, required: SecurityClearance) -> bool:
        return self.get_clearance(player) >= required

    def is_level4(self, player) -> bool:
        """Fast-path check using the in-memory cache."""
        return str(player.unique_id) in self._level4_players

    def get_level4_players(self) -> Set[str]:
        return self._level4_players.copy()

    def get_stored_password_hash(self) -> Optional[str]:
        return self._db.get("config", "op_password_hash")

    def set_password_hash(self, password_hash: str):
        self._db.set("config", "op_password_hash", password_hash)

    def has_password_set(self) -> bool:
        return self._db.has("config", "op_password_hash")
