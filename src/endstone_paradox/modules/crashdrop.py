# crashdrop.py - Anti-Crash-Drop Module
# Removes items dropped near where a player disconnected to prevent crash-dupe exploits.

import time
from collections import deque
from endstone_paradox.modules.base import BaseModule


class CrashDropModule(BaseModule):
    """Prevents crash/disconnect duplication exploits.

    When a player disconnects (crashes, kicks, or leaves), we record their
    last known position. Any item entities that spawn near that position
    within a short time window are likely duped items from a crash exploit
    and are removed.

    Also monitors for suspicious disconnect patterns (rapid reconnect cycles).
    """

    @property
    def name(self) -> str:
        return "crashdrop"

    @property
    def check_interval(self) -> int:
        return 4  # Every 4 ticks (0.2s) — fast location tracking

    def on_start(self):
        # Last known location for each player: {uuid: {location, dimension_id}}
        self._player_locations = {}
        # Recent disconnects: deque of {location, dimension_id, time, player_name, uuid}
        self._recent_disconnects = deque(maxlen=50)
        # Disconnect frequency tracking: {uuid: deque of timestamps}
        self._disconnect_frequency = {}
        self.logger.info("  §2[§7Paradox§2]§a CrashDrop: Anti-crash-dupe active")

    def on_stop(self):
        self._player_locations.clear()
        self._recent_disconnects.clear()
        self._disconnect_frequency.clear()

    def _apply_sensitivity(self):
        """Higher sensitivity = wider radius, longer time window."""
        # Removal radius squared: sens 5 → 9 (3 blocks), sens 10 → 25 (5 blocks)
        self._removal_radius_sq = self._scale(9.0, invert=True)
        # Time window: sens 5 → 3s, sens 10 → 5s
        self._time_window = self._scale(3.0, invert=True)
        # Rapid disconnect threshold: disconnects in 60s to flag
        self._rapid_dc_threshold = int(self._scale(3, invert=True))

    def check(self):
        """Track all online player locations every few ticks."""
        for player in self.plugin.server.online_players:
            try:
                uuid = str(player.unique_id)
                loc = player.location
                self._player_locations[uuid] = {
                    "location": (loc.x, loc.y, loc.z),
                    "dimension_id": str(player.dimension.id) if hasattr(player, 'dimension') else "overworld",
                    "name": player.name,
                }
            except Exception:
                pass

        # Prune old disconnect records
        now = time.time()
        while (self._recent_disconnects and
               now - self._recent_disconnects[0]["time"] > self._time_window + 2):
            self._recent_disconnects.popleft()

    def on_player_leave(self, player):
        """Record disconnect location for crash-drop detection."""
        uuid = str(player.unique_id)
        last_data = self._player_locations.pop(uuid, None)
        if last_data:
            now = time.time()
            self._recent_disconnects.append({
                "location": last_data["location"],
                "dimension_id": last_data["dimension_id"],
                "time": now,
                "player_name": last_data["name"],
                "player_uuid": uuid,
            })

            # Track disconnect frequency
            dc_times = self._disconnect_frequency.setdefault(uuid, deque(maxlen=20))
            dc_times.append(now)
            # Clean old entries
            while dc_times and (now - dc_times[0]) > 60.0:
                dc_times.popleft()

            # Rapid disconnect detection
            if len(dc_times) >= self._rapid_dc_threshold:
                self.alert_admins(
                    f"§c{last_data['name']}§e rapid disconnect pattern: "
                    f"{len(dc_times)} disconnects in 60s (possible crash-dupe)"
                )
                self._log_event("rapid_disconnect", {
                    "player": last_data["name"],
                    "uuid": uuid,
                    "disconnects_in_60s": len(dc_times),
                    "location": f"{last_data['location'][0]:.0f}, {last_data['location'][1]:.0f}, {last_data['location'][2]:.0f}",
                    "dimension": last_data["dimension_id"],
                })

    def should_remove_item_entity(self, entity_pos, dimension_id):
        """Check if an item entity spawned near a recent disconnect location.
        Returns True if the item should be removed (suspected crash-dupe)."""
        now = time.time()
        ex, ey, ez = entity_pos

        for dc in self._recent_disconnects:
            if now - dc["time"] > self._time_window:
                continue
            if dc["dimension_id"] != dimension_id:
                continue

            dx = ex - dc["location"][0]
            dy = ey - dc["location"][1]
            dz = ez - dc["location"][2]
            dist_sq = dx * dx + dy * dy + dz * dz

            if dist_sq <= self._removal_radius_sq:
                self._log_event("crash_drop_removed", {
                    "player": dc["player_name"],
                    "uuid": dc["player_uuid"],
                    "item_pos": f"{ex:.0f}, {ey:.0f}, {ez:.0f}",
                    "disconnect_pos": f"{dc['location'][0]:.0f}, {dc['location'][1]:.0f}, {dc['location'][2]:.0f}",
                    "dimension": dimension_id,
                    "time_after_dc": f"{now - dc['time']:.1f}s",
                })
                return True

        return False

    def _log_event(self, event_type, details):
        """Log event to DB for web UI."""
        event = {
            "type": event_type,
            "details": details,
            "time": time.time(),
        }
        events = self.db.get("crashdrop_log", "events", [])
        if not isinstance(events, list):
            events = []
        events.append(event)
        if len(events) > 200:
            events = events[-200:]
        self.db.set("crashdrop_log", "events", events)
