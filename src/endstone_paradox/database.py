# database.py - SQLite persistence layer
# Key-value store backed by sqlite3, values serialized as JSON.
# Each "table" is a real SQLite table with (key, value, updated_at).

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional


class ParadoxDatabase:
    """SQLite key-value store. Each logical namespace is its own table."""

    DEFAULT_TABLES = [
        "modules", "config", "players", "bans", "channels",
        "whitelist", "allowlist", "disabled_commands", "homes",
        "ranks", "player_data", "spoof_log", "tpa_requests",
        "pvp_data", "frozen_players", "vanished_players",
        "violations",
    ]

    DB_VERSION = 2

    def __init__(self, data_folder: Path, logger=None):
        self._data_folder = data_folder
        self._logger = logger
        self._db_path = data_folder / "paradox.db"
        self._lock = threading.Lock()

        data_folder.mkdir(parents=True, exist_ok=True)

        self._conn = self._create_connection()
        self._init_schema()

    def _create_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _init_schema(self):
        with self._lock:
            cursor = self._conn.cursor()

            # version tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS _meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

            for table in self.DEFAULT_TABLES:
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS [{table}] (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at REAL DEFAULT (julianday('now'))
                    )
                """)

            cursor.execute(
                "INSERT OR REPLACE INTO _meta (key, value) VALUES (?, ?)",
                ("db_version", str(self.DB_VERSION)),
            )
            self._conn.commit()

    def _ensure_table(self, table: str):
        """Create table on-the-fly if it doesn't exist yet."""
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
        with self._lock:
            try:
                cursor = self._conn.execute(
                    f"SELECT 1 FROM [{table}] WHERE key = ?", (key,)
                )
                return cursor.fetchone() is not None
            except sqlite3.OperationalError:
                return False

    def keys(self, table: str) -> List[str]:
        with self._lock:
            try:
                cursor = self._conn.execute(f"SELECT key FROM [{table}]")
                return [row[0] for row in cursor.fetchall()]
            except sqlite3.OperationalError:
                return []

    def get_all(self, table: str) -> Dict[str, Any]:
        with self._lock:
            try:
                cursor = self._conn.execute(
                    f"SELECT key, value FROM [{table}]"
                )
                return {row[0]: json.loads(row[1]) for row in cursor.fetchall()}
            except sqlite3.OperationalError:
                return {}

    def count(self, table: str) -> int:
        with self._lock:
            try:
                cursor = self._conn.execute(f"SELECT COUNT(*) FROM [{table}]")
                return cursor.fetchone()[0]
            except sqlite3.OperationalError:
                return 0

    def clear_table(self, table: str):
        with self._lock:
            try:
                self._conn.execute(f"DELETE FROM [{table}]")
                self._conn.commit()
            except sqlite3.OperationalError:
                pass

    def list_tables(self) -> List[str]:
        with self._lock:
            cursor = self._conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name != '_meta'"
            )
            return [row[0] for row in cursor.fetchall()]

    def execute_raw(self, query: str, params: tuple = ()) -> List[tuple]:
        """For /ac-debug-db — run arbitrary SQL. Be careful with this."""
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
        with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None

    def reconnect(self):
        """Close and re-open the database connection (for plugin reload)."""
        self.close()
        self._conn = self._create_connection()
        self._init_schema()

    @property
    def db_path(self) -> Path:
        return self._db_path

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
