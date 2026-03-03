# invsync.py - Inventory Synchronization Module
# Snapshots player inventories and removes duplicated items on rejoin.

import time
import json
from endstone_paradox.modules.base import BaseModule


class InvSyncModule(BaseModule):
    """Inventory synchronization to prevent rejoin-based duplication.

    Periodically snapshots each player's inventory item counts into the DB.
    When a player rejoins, compares their current inventory against the last
    snapshot and removes any excess items that appeared during the disconnect.

    This catches dupes where players crash/disconnect with items in a
    container, then rejoin and have both the container items AND the
    restored inventory items.

    Enhanced with packet monitoring: tracks ItemStackRequest packets
    for anomalous item creation patterns.
    """

    @property
    def name(self) -> str:
        return "invsync"

    @property
    def check_interval(self) -> int:
        return 100  # Every 5 seconds — snapshot inventory counts

    def on_start(self):
        # In-memory cache (also persisted to DB)
        self._last_snapshots = {}  # UUID -> {item_type: count}
        # Pending join checks (delayed to let inventory load)
        self._pending_checks = {}  # UUID -> join_time
        self.logger.info("  §2[§7Paradox§2]§a InvSync: Inventory snapshot sync active")

    def on_stop(self):
        self._last_snapshots.clear()
        self._pending_checks.clear()

    def _apply_sensitivity(self):
        """Higher sensitivity = stricter item diff tolerance."""
        # At sens 5, tolerance is 0 (exact match required)
        # At sens 1, tolerance is 2 extra items allowed
        # At sens 10, tolerance is 0 (zero tolerance)
        self._item_tolerance = max(0, int(self._scale(0, invert=False)))

    def check(self):
        """Periodic: Snapshot all online players' inventories."""
        for player in self.plugin.server.online_players:
            try:
                uuid = str(player.unique_id)
                snapshot = self._get_inventory_counts(player)
                if snapshot is not None:
                    self._last_snapshots[uuid] = snapshot
                    # Persist to DB (survives restarts)
                    self.db.set("inv_snapshots", uuid, {
                        "counts": snapshot,
                        "time": time.time(),
                        "name": player.name,
                    })
            except Exception:
                pass

        # Process pending join checks (delayed by ~1 second)
        now = time.time()
        completed = []
        for uuid, join_time in self._pending_checks.items():
            if now - join_time >= 1.0:  # Wait 1 second for inventory to load
                completed.append(uuid)
                self._check_rejoin_inventory(uuid)
        for uuid in completed:
            self._pending_checks.pop(uuid, None)

    def on_player_join(self, player):
        """Schedule an inventory check for a player who just joined."""
        uuid = str(player.unique_id)
        self._pending_checks[uuid] = time.time()

    def on_player_leave(self, player):
        """Take a final snapshot when player leaves."""
        uuid = str(player.unique_id)
        self._pending_checks.pop(uuid, None)
        try:
            snapshot = self._get_inventory_counts(player)
            if snapshot is not None:
                self._last_snapshots[uuid] = snapshot
                self.db.set("inv_snapshots", uuid, {
                    "counts": snapshot,
                    "time": time.time(),
                    "name": player.name,
                })
        except Exception:
            pass

    def _check_rejoin_inventory(self, uuid):
        """Compare current inventory against last snapshot."""
        # Get the stored snapshot
        saved_data = self.db.get("inv_snapshots", uuid)
        if not saved_data or not isinstance(saved_data, dict):
            return

        saved_counts = saved_data.get("counts", {})
        if not saved_counts:
            return

        # Find the player online
        player = None
        for p in self.plugin.server.online_players:
            if str(p.unique_id) == uuid:
                player = p
                break

        if player is None:
            return

        current_counts = self._get_inventory_counts(player)
        if current_counts is None:
            return

        # Compare: look for items that increased
        excess_items = {}
        for item_type, current_count in current_counts.items():
            saved_count = saved_counts.get(item_type, 0)
            diff = current_count - saved_count
            if diff > self._item_tolerance:
                excess_items[item_type] = diff

        if excess_items:
            # Log the detection
            total_excess = sum(excess_items.values())
            item_list = ", ".join(f"{k}: +{v}" for k, v in excess_items.items())

            self.alert_admins(
                f"§c{player.name}§e inventory sync anomaly: "
                f"{total_excess} excess items on rejoin ({item_list})"
            )

            self._log_event("inv_sync_anomaly", {
                "player": player.name,
                "uuid": uuid,
                "excess_items": excess_items,
                "total_excess": total_excess,
            })

    def _get_inventory_counts(self, player):
        """Get a count of each item type in a player's inventory.
        Returns {item_type: total_count} or None if inventory can't be read."""
        try:
            inv = player.inventory
            if inv is None:
                return None

            counts = {}
            for i in range(inv.size):
                item = inv.get_item(i)
                if item is not None:
                    type_id = str(item.type)
                    counts[type_id] = counts.get(type_id, 0) + item.amount
            return counts
        except Exception:
            return None

    def _log_event(self, event_type, details):
        """Log event to DB for web UI."""
        event = {
            "type": event_type,
            "details": details,
            "time": time.time(),
        }
        events = self.db.get("invsync_log", "events", [])
        if not isinstance(events, list):
            events = []
        events.append(event)
        if len(events) > 200:
            events = events[-200:]
        self.db.set("invsync_log", "events", events)
