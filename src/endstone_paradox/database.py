"""
Paradox AntiCheat - SQLite Database System

Provides persistent key-value storage backed by SQLite3 with JSON-serialized values.
Supports multiple named tables, WAL mode for concurrent reads, and admin-accessible
via /ac-debug-db command or direct file access.
"""

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional


class ParadoxDatabase:
    """
    SQLite-backed persistent key-value store for Paradox AntiCheat.

    Each logical 'database' is a table in a single SQLite file.
    Values are JSON-serialized for flexibility.
    """

    # Default tables created on initialization
    DEFAULT_TABLES = [
        "modules",
        "config",
        "players",
        "bans",
        "channels",
        "whitelist",
        "allowlist",
        "disabled_commands",
        "homes",
        "ranks",
        "player_data",
        "spoof_log",
        "tpa_requests",
        "pvp_data",
        "frozen_players",
        "vanished_players",
    ]

    DB_VERSION = 1

    def __init__(self, data_folder: Path, logger=None):
        """
        Initialize the database.

        Args:
            data_folder: Path to the plugin's data folder.
            logger: Optional logger instance.
        """
        self._data_folder = data_folder
        self._logger = logger
        self._db_path = data_folder / "paradox.db"
        self._lock = threading.Lock()

        # Ensure data folder exists
        data_folder.mkdir(parents=True, exist_ok=True)

        # Initialize connection and schema
        self._conn = self._create_connection()
        self._init_schema()

    def _create_connection(self) -> sqlite3.Connection:
        """Create a new SQLite connection with WAL mode."""
        conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _init_schema(self):
        """Initialize all default tables and the version tracking table."""
        with self._lock:
            cursor = self._conn.cursor()

            # Version tracking table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS _meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

            # Create all default tables
            for table in self.DEFAULT_TABLES:
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS [{table}] (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at REAL DEFAULT (julianday('now'))
                    )
                """)

            # Store version
            cursor.execute(
                "INSERT OR REPLACE INTO _meta (key, value) VALUES (?, ?)",
                ("db_version", str(self.DB_VERSION)),
            )

            self._conn.commit()

    def _ensure_table(self, table: str):
        """Create a table if it doesn't exist (for dynamic table creation)."""
        with self._lock:
            self._conn.execute(f"""
                CREATE TABLE IF NOT EXISTS [{table}] (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at REAL DEFAULT (julianday('now'))
                )
            """)
            self._conn.commit()

    def get(self, table: str, key: str, default: Any = None) -> Any:
        """
        Get a value from a table.

        Args:
            table: Table name.
            key: Key to look up.
            default: Default value if key not found.

        Returns:
            The deserialized value, or default if not found.
        """
        with self._lock:
            try:
                cursor = self._conn.execute(
                    f"SELECT value FROM [{table}] WHERE key = ?", (key,)
                )
                row = cursor.fetchone()
                if row is not None:
                    return json.loads(row[0])
                return default
            except sqlite3.OperationalError:
                return default

    def set(self, table: str, key: str, value: Any):
        """
        Set a value in a table.

        Args:
            table: Table name.
            key: Key to store under.
            value: Value to store (will be JSON-serialized).
        """
        self._ensure_table(table)
        serialized = json.dumps(value)
        with self._lock:
            self._conn.execute(
                f"""INSERT OR REPLACE INTO [{table}] (key, value, updated_at)
                    VALUES (?, ?, julianday('now'))""",
                (key, serialized),
            )
            self._conn.commit()

    def delete(self, table: str, key: str) -> bool:
        """
        Delete a key from a table.

        Args:
            table: Table name.
            key: Key to delete.

        Returns:
            True if the key existed and was deleted.
        """
        with self._lock:
            try:
                cursor = self._conn.execute(
                    f"DELETE FROM [{table}] WHERE key = ?", (key,)
                )
                self._conn.commit()
                return cursor.rowcount > 0
            except sqlite3.OperationalError:
                return False

    def has(self, table: str, key: str) -> bool:
        """Check if a key exists in a table."""
        with self._lock:
            try:
                cursor = self._conn.execute(
                    f"SELECT 1 FROM [{table}] WHERE key = ?", (key,)
                )
                return cursor.fetchone() is not None
            except sqlite3.OperationalError:
                return False

    def keys(self, table: str) -> List[str]:
        """Get all keys in a table."""
        with self._lock:
            try:
                cursor = self._conn.execute(f"SELECT key FROM [{table}]")
                return [row[0] for row in cursor.fetchall()]
            except sqlite3.OperationalError:
                return []

    def get_all(self, table: str) -> Dict[str, Any]:
        """Get all key-value pairs in a table."""
        with self._lock:
            try:
                cursor = self._conn.execute(
                    f"SELECT key, value FROM [{table}]"
                )
                return {row[0]: json.loads(row[1]) for row in cursor.fetchall()}
            except sqlite3.OperationalError:
                return {}

    def count(self, table: str) -> int:
        """Get the number of entries in a table."""
        with self._lock:
            try:
                cursor = self._conn.execute(
                    f"SELECT COUNT(*) FROM [{table}]"
                )
                return cursor.fetchone()[0]
            except sqlite3.OperationalError:
                return 0

    def clear_table(self, table: str):
        """Remove all entries from a table."""
        with self._lock:
            try:
                self._conn.execute(f"DELETE FROM [{table}]")
                self._conn.commit()
            except sqlite3.OperationalError:
                pass

    def list_tables(self) -> List[str]:
        """List all user tables (excluding _meta)."""
        with self._lock:
            cursor = self._conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name != '_meta'"
            )
            return [row[0] for row in cursor.fetchall()]

    def execute_raw(self, query: str, params: tuple = ()) -> List[tuple]:
        """
        Execute a raw SQL query (for admin debug access).

        Args:
            query: SQL query string.
            params: Query parameters.

        Returns:
            List of result rows.
        """
        with self._lock:
            try:
                cursor = self._conn.execute(query, params)
                if query.strip().upper().startswith("SELECT"):
                    return cursor.fetchall()
                self._conn.commit()
                return []
            except sqlite3.Error as e:
                if self._logger:
                    self._logger.error(f"SQL error: {e}")
                raise

    def close(self):
        """Close the database connection."""
        with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None

    def __del__(self):
        """Ensure connection is closed on garbage collection."""
        try:
            self.close()
        except Exception:
            pass
