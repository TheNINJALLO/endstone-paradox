# analytics_collector.py - Analytics Data Collector (Tier 3)
# Collects violation data into time-bucketed summaries for the analytics dashboard.

import time
import json
from collections import defaultdict


def _hour_key(ts: float = None) -> str:
    """Convert a timestamp to an hourly bucket key like '2024-03-07T22'."""
    if ts is None:
        ts = time.time()
    t = time.gmtime(ts)
    return f"{t.tm_year:04d}-{t.tm_mon:02d}-{t.tm_mday:02d}T{t.tm_hour:02d}"


class AnalyticsCollector:
    """Collects and aggregates violation / enforcement metrics for dashboards.

    Data is stored in the 'analytics' DB table as hourly buckets.
    Designed to be lightweight — called from the violation engine hook.
    """

    def __init__(self, db, logger=None):
        self._db = db
        self._logger = logger
        self._db._ensure_table("analytics")

        # In-memory counters for the current hour (flushed periodically)
        self._current_hour = _hour_key()
        self._violations_total = 0
        self._violations_by_module = defaultdict(int)
        self._flagged_players = set()
        self._actions = defaultdict(int)  # action -> count

    # ── Primary API (called from violation engine hook) ───────

    def record_violation(self, module: str, severity: int, action: str,
                         player_uuid: str = None):
        """Record a single violation event.

        Args:
            module: Module name that emitted the violation
            severity: Severity level (1-5)
            action: Enforcement action taken (warn, cancel, setback, kick, ban)
            player_uuid: UUID of the flagged player
        """
        current = _hour_key()

        # If the hour rolled over, flush the previous hour
        if current != self._current_hour:
            self._flush_hour()
            self._current_hour = current

        self._violations_total += 1
        self._violations_by_module[module] += 1
        if action:
            self._actions[action] += 1
        if player_uuid:
            self._flagged_players.add(player_uuid)

    # ── Query API (for web dashboard) ────────────────────────

    def get_summary(self, hours: int = 24) -> dict:
        """Get aggregated analytics for the last N hours.

        Returns:
            dict with keys: violations_by_hour, modules, actions, player_count
        """
        # First flush current data
        self._flush_hour()

        now = time.time()
        result = {
            "violations_by_hour": [],   # [{hour, count}, ...]
            "modules": {},              # module -> total_count
            "actions": {},              # action -> total_count
            "total_violations": 0,
            "unique_players": 0,
        }

        all_players = set()

        for h in range(hours):
            ts = now - (h * 3600)
            hour = _hour_key(ts)
            data = self._db.get("analytics", hour, {})
            if not isinstance(data, dict):
                data = {}

            count = data.get("violations", 0)
            result["violations_by_hour"].append({
                "hour": hour,
                "count": count,
            })
            result["total_violations"] += count

            # Aggregate modules
            for mod, cnt in data.get("modules", {}).items():
                result["modules"][mod] = result["modules"].get(mod, 0) + cnt

            # Aggregate actions
            for act, cnt in data.get("actions", {}).items():
                result["actions"][act] = result["actions"].get(act, 0) + cnt

            # Aggregate players
            players = data.get("players", [])
            if isinstance(players, list):
                all_players.update(players)

        # Reverse so oldest is first (for charts)
        result["violations_by_hour"].reverse()
        result["unique_players"] = len(all_players)

        return result

    def get_top_players(self, n: int = 10) -> list:
        """Get the top N players by violation count (from violations DB table).

        Returns:
            List of dicts with uuid, name, count, last_module.
        """
        try:
            all_violations = self._db.get_all("violations")
        except Exception:
            return []

        player_counts = defaultdict(lambda: {"count": 0, "name": "?", "last_module": "?"})

        for key, data in all_violations.items():
            if not isinstance(data, dict):
                continue
            uuid_str = data.get("uuid", key)
            name = data.get("name", "?")
            module = data.get("module", "?")
            player_counts[uuid_str]["count"] += 1
            player_counts[uuid_str]["name"] = name
            player_counts[uuid_str]["last_module"] = module

        # Sort by count descending
        sorted_players = sorted(
            player_counts.items(),
            key=lambda x: x[1]["count"],
            reverse=True,
        )[:n]

        return [
            {
                "uuid": uuid_str,
                "name": data["name"],
                "count": data["count"],
                "last_module": data["last_module"],
            }
            for uuid_str, data in sorted_players
        ]

    # ── Internal ─────────────────────────────────────────────

    def _flush_hour(self):
        """Persist the current hour's counters to DB and reset."""
        if self._violations_total == 0:
            return  # Nothing to flush

        hour = self._current_hour
        existing = self._db.get("analytics", hour, {})
        if not isinstance(existing, dict):
            existing = {}

        # Merge counters
        existing["violations"] = existing.get("violations", 0) + self._violations_total

        # Merge module counts
        modules = existing.get("modules", {})
        for mod, cnt in self._violations_by_module.items():
            modules[mod] = modules.get(mod, 0) + cnt
        existing["modules"] = modules

        # Merge actions
        actions = existing.get("actions", {})
        for act, cnt in self._actions.items():
            actions[act] = actions.get(act, 0) + cnt
        existing["actions"] = actions

        # Merge player set
        players = set(existing.get("players", []))
        players.update(self._flagged_players)
        existing["players"] = list(players)

        self._db.set("analytics", hour, existing)

        # Reset in-memory counters
        self._violations_total = 0
        self._violations_by_module.clear()
        self._flagged_players.clear()
        self._actions.clear()

    def flush(self):
        """Public flush — called on shutdown."""
        self._flush_hour()
