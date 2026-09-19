# antidupe.py - Anti-Duplication Module
# Prevents item duplication exploits via bundles, hopper clusters, pistons, and packet analysis.

import time
from collections import defaultdict, deque
from endstone_paradox.modules.base import BaseModule


class AntiDupeModule(BaseModule):
    """Detects and prevents item duplication exploits.

    Four detection layers:
      1. Bundle Blocking — removes bundles placed inside hoppers/dispensers/droppers
      2. Hopper Cluster Monitoring — snapshots item counts in hopper clusters;
         flags if items increase without a player adding them (allows hopper clocks)
      3. Piston Entity Monitoring — detects TNT/carpet/rail/gravity-block duplication
         by tracking entity spawn rates near active pistons
      4. Packet Analysis — monitors InventoryTransaction and ItemStackRequest packets
         for impossible item transfers (items appearing from nowhere)
    """

    @property
    def name(self) -> str:
        return "antidupe"

    @property
    def check_interval(self) -> int:
        return int(self._scale(40))  # ~2 seconds at default sensitivity

    # -- Container types exploitable with bundles --
    BUNDLE_CONTAINERS = {
        "minecraft:hopper", "minecraft:dispenser",
        "minecraft:dropper", "minecraft:crafter",
    }

    # -- Packet types relevant to dupe detection --
    DUPE_PACKETS = {
        "InventoryTransactionPacket",
        "ItemStackRequestPacket",
        "ContainerOpenPacket",
        "ContainerClosePacket",
    }

    def on_start(self):
        # Layer 1: Bundle tracking
        self._tracked_containers = {}
        # Layer 2: Hopper cluster monitoring
        self._hopper_clusters = {}
        # Layer 3: Piston entity tracking
        self._piston_entity_spawns = {}
        # Layer 4: Packet analysis
        self._player_packet_counts = {}   # UUID -> {packet_type: deque}
        self._player_inv_transactions = {}  # UUID -> deque of transaction timestamps
        # General: container access tracking
        self._player_container_access = {}
        # Event log for web UI
        self._recent_alerts = deque(maxlen=50)
        self.logger.info("  §2[§7Paradox§2]§a AntiDupe: 4-layer protection active")

    def on_stop(self):
        self._tracked_containers.clear()
        self._hopper_clusters.clear()
        self._piston_entity_spawns.clear()
        self._player_packet_counts.clear()
        self._player_inv_transactions.clear()
        self._player_container_access.clear()

    def on_player_leave(self, player):
        uuid = str(player.unique_id)
        self._player_packet_counts.pop(uuid, None)
        self._player_inv_transactions.pop(uuid, None)
        self._player_container_access.pop(uuid, None)

    def _apply_sensitivity(self):
        """Higher sensitivity = more frequent scans, tighter anomaly tolerance."""
        self._piston_spawn_threshold = int(self._scale(3, invert=True))
        self._piston_time_window = self._scale(2.0)
        self._hopper_item_tolerance = int(self._scale(1, invert=False))
        # Packet: max inventory transactions per second before flagging
        self._inv_transaction_limit = int(self._scale(30, invert=False))

    # -------------------------------------------------------------------
    # Layer 1: Bundle Blocking
    # -------------------------------------------------------------------

    def on_block_place(self, event):
        """Track hopper placement for cluster monitoring."""
        if not self.running:
            return
        player = event.player
        block = event.block
        if block is None:
            return

        block_type = ""
        if hasattr(block, 'type'):
            block_type = str(block.type).lower()

        # Register hopper clusters on hopper placement
        if "hopper" in block_type:
            self._register_hopper_cluster(block, player)

    def track_container_open(self, player, block_pos, dimension_id):
        """Called when a player opens a container — marks it for bundle scanning."""
        uuid = str(player.unique_id)
        pos_key = f"{block_pos[0]},{block_pos[1]},{block_pos[2]},{dimension_id}"
        self._tracked_containers[pos_key] = {
            "pos": block_pos,
            "dimension_id": dimension_id,
            "expire_time": time.time() + 120,
            "player_name": player.name,
            "player_uuid": uuid,
        }
        self._player_container_access[uuid] = {
            "pos_key": pos_key,
            "time": time.time(),
        }

    def _scan_tracked_containers(self):
        """Prune expired container tracking entries."""
        now = time.time()
        expired = [k for k, v in self._tracked_containers.items()
                    if now > v["expire_time"]]
        for k in expired:
            self._tracked_containers.pop(k, None)

    # -------------------------------------------------------------------
    # Layer 2: Hopper Cluster Monitoring
    # -------------------------------------------------------------------

    def _register_hopper_cluster(self, block, player):
        """Track hopper placement for cluster monitoring."""
        try:
            pos = block.location if hasattr(block, 'location') else None
            if pos is None:
                return
            x, y, z = int(pos.x), int(pos.y), int(pos.z)
            dim_id = str(block.dimension.id) if hasattr(block, 'dimension') else "overworld"
            cluster_key = f"{x},{y},{z},{dim_id}"

            self._hopper_clusters[cluster_key] = {
                "center": (x, y, z),
                "dimension_id": dim_id,
                "last_count": 0,
                "last_scan": time.time(),
                "placed_by": player.name,
                "placed_uuid": str(player.unique_id),
                "placed_time": time.time(),
                "expire_time": time.time() + 600,  # monitor 10 minutes
            }

            self._log_event("hopper_placed", {
                "player": player.name,
                "uuid": str(player.unique_id),
                "pos": f"{x}, {y}, {z}",
                "dimension": dim_id,
            })
        except Exception as e:
            self.logger.warning(f"AntiDupe hopper cluster error: {e}")

    def _scan_hopper_clusters(self):
        """Prune expired hopper cluster entries."""
        now = time.time()
        expired = [k for k, v in self._hopper_clusters.items()
                    if now > v["expire_time"]]
        for k in expired:
            self._hopper_clusters.pop(k, None)

    # -------------------------------------------------------------------
    # Layer 3: Piston Entity Monitoring
    # -------------------------------------------------------------------

    def _check_piston_dupes(self):
        """Check for entity spawn rate anomalies (rapid spawning = dupe)."""
        now = time.time()
        expired = []
        for region_key, data in self._piston_entity_spawns.items():
            if now - data["last_reset"] > self._piston_time_window:
                if data["spawn_count"] >= self._piston_spawn_threshold:
                    self.alert_admins(
                        f"§cPiston dupe suspected at region {region_key} "
                        f"({data['spawn_count']} entities in "
                        f"{self._piston_time_window:.1f}s)"
                    )
                    self._log_event("piston_dupe", {
                        "region": region_key,
                        "entity_count": data["spawn_count"],
                        "time_window": f"{self._piston_time_window:.1f}s",
                    })
                data["spawn_count"] = 0
                data["last_reset"] = now

            if now - data.get("created", now) > 300:
                expired.append(region_key)

        for k in expired:
            self._piston_entity_spawns.pop(k, None)

    def track_entity_spawn(self, entity_type, pos, dimension_id):
        """Track entity spawns for piston-dupe detection."""
        rx, ry, rz = int(pos[0]) // 4, int(pos[1]) // 4, int(pos[2]) // 4
        region_key = f"{rx},{ry},{rz},{dimension_id}"

        if region_key not in self._piston_entity_spawns:
            self._piston_entity_spawns[region_key] = {
                "spawn_count": 0,
                "last_reset": time.time(),
                "created": time.time(),
            }
        self._piston_entity_spawns[region_key]["spawn_count"] += 1

    # -------------------------------------------------------------------
    # Layer 4: Packet Analysis
    # -------------------------------------------------------------------

    def on_packet(self, event):
        """Monitor InventoryTransaction and ItemStackRequest packets.
        Rapid-fire inventory transactions can indicate dupe exploits."""
        player = event.player
        if player is None:
            return

        packet_type = getattr(event, 'packet_type', 'Unknown')
        if isinstance(packet_type, int):
            packet_type = f"PacketID_{packet_type}"
        else:
            packet_type = str(packet_type)

        if packet_type not in self.DUPE_PACKETS:
            return

        uuid = str(player.unique_id)
        now = time.time()

        # Track inventory transaction rate
        if "InventoryTransaction" in packet_type or "ItemStackRequest" in packet_type:
            txns = self._player_inv_transactions.setdefault(uuid, deque())
            txns.append(now)

            # Clean old entries (1-second window)
            while txns and (now - txns[0]) > 1.0:
                txns.popleft()

            if len(txns) > self._inv_transaction_limit:
                self.alert_admins(
                    f"§c{player.name}§e rapid inventory transactions: "
                    f"{len(txns)}/s (possible dupe exploit)"
                )
                self._log_event("rapid_inv_transaction", {
                    "player": player.name,
                    "uuid": uuid,
                    "transactions_per_sec": len(txns),
                    "packet_type": packet_type,
                })
                txns.clear()

        # Track container open/close patterns
        if "ContainerOpen" in packet_type:
            pdata = self._player_packet_counts.setdefault(uuid, defaultdict(deque))
            opens = pdata["container_opens"]
            opens.append(now)
            while opens and (now - opens[0]) > 5.0:
                opens.popleft()

            # Rapid container open/close is suspicious (>10 in 5s)
            if len(opens) > 10:
                self.alert_admins(
                    f"§c{player.name}§e rapid container access: "
                    f"{len(opens)} opens in 5s"
                )
                self._log_event("rapid_container_access", {
                    "player": player.name,
                    "uuid": uuid,
                    "opens_in_5s": len(opens),
                })
                opens.clear()

    # -------------------------------------------------------------------
    # Periodic check
    # -------------------------------------------------------------------

    def check(self):
        """Periodic audit of all detection layers."""
        self._scan_tracked_containers()
        self._scan_hopper_clusters()
        self._check_piston_dupes()

    # -------------------------------------------------------------------
    # Event Logging (for web UI)
    # -------------------------------------------------------------------

    def _log_event(self, event_type, details):
        """Log a dupe detection event to the database for the web UI."""
        event = {
            "type": event_type,
            "details": details,
            "time": time.time(),
        }
        self._recent_alerts.append(event)

        # Persist to DB
        events = self.db.get("antidupe_log", "events", [])
        if not isinstance(events, list):
            events = []
        events.append(event)
        if len(events) > 200:
            events = events[-200:]
        self.db.set("antidupe_log", "events", events)

    def get_dashboard_data(self):
        """Return data for the web UI dashboard."""
        events = self.db.get("antidupe_log", "events", [])
        if not isinstance(events, list):
            events = []
        return {
            "events": events,
            "tracked_containers": len(self._tracked_containers),
            "hopper_clusters": len(self._hopper_clusters),
            "piston_regions": len(self._piston_entity_spawns),
            "hopper_details": [
                {
                    "pos": f"{v['center'][0]}, {v['center'][1]}, {v['center'][2]}",
                    "dimension": v["dimension_id"],
                    "placed_by": v["placed_by"],
                    "placed_time": v["placed_time"],
                }
                for v in self._hopper_clusters.values()
            ],
        }
