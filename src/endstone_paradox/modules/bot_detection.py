# bot_detection.py - Bot Detection Module (Tier 3)
# Behavioral entropy analysis, connection pattern analysis, and honeypot blocks.

import math
import time
from collections import defaultdict, deque
from endstone_paradox.modules.base import BaseModule


# --- Entropy thresholds ---
# Bots tend to move with very uniform or very random patterns
MIN_ENTROPY = 0.3        # Below this = too uniform (bot-like)
MAX_ENTROPY = 3.8        # Above this = artificially random (randomized bot)
ENTROPY_WINDOW = 100     # Number of movement samples per window

# --- Connection pattern thresholds ---
SHORT_SESSION_THRESHOLD = 30.0    # Sessions shorter than 30s are suspicious
REJOIN_WINDOW = 300.0             # Check rejoins within last 5 minutes
MAX_SHORT_SESSIONS = 4            # More than 4 short sessions = suspicious


class BotDetectionModule(BaseModule):
    """Detects automated/bot players through behavioral analysis.

    Three detection layers:
    1. Behavioral Entropy — movement direction change patterns
    2. Connection Patterns — rapid join/leave cycling
    3. Honeypot Blocks — admin-placed trap blocks
    """

    @property
    def name(self) -> str:
        return "botdetection"

    @property
    def check_interval(self) -> int:
        return 100  # Check every 5 seconds

    def on_start(self):
        # Per-player movement tracking: uuid -> deque of direction deltas
        self._movement_history = defaultdict(lambda: deque(maxlen=ENTROPY_WINDOW))
        # Per-player last known position: uuid -> (x, y, z, yaw, pitch)
        self._last_positions = {}
        # Connection tracking: uuid -> list of (join_time, leave_time)
        self._session_log = defaultdict(list)
        # Honeypot blocks: set of (dim, x, y, z) tuples
        self._honeypots = set()
        self._load_honeypots()

    def on_stop(self):
        self._movement_history.clear()
        self._last_positions.clear()
        self._session_log.clear()

    def _load_honeypots(self):
        """Load honeypot block positions from DB."""
        stored = self.db.get("honeypots", "positions", [])
        if isinstance(stored, list):
            self._honeypots = {tuple(pos) for pos in stored if len(pos) == 4}

    def _save_honeypots(self):
        """Persist honeypot positions to DB."""
        self.db.set("honeypots", "positions", [list(pos) for pos in self._honeypots])

    def add_honeypot(self, dimension: str, x: int, y: int, z: int):
        """Admin API: Register a block as a honeypot trap."""
        self._honeypots.add((dimension, x, y, z))
        self._save_honeypots()

    def remove_honeypot(self, dimension: str, x: int, y: int, z: int) -> bool:
        """Admin API: Remove a honeypot registration."""
        key = (dimension, x, y, z)
        if key in self._honeypots:
            self._honeypots.discard(key)
            self._save_honeypots()
            return True
        return False

    def on_player_join(self, player):
        uuid_str = str(player.unique_id)
        self._session_log[uuid_str].append({
            "join": time.time(),
            "leave": None,
        })
        # Check connection patterns on join
        self._check_connection_pattern(player, uuid_str)

    def on_player_leave(self, player):
        uuid_str = str(player.unique_id)
        now = time.time()

        # Mark session end
        sessions = self._session_log.get(uuid_str, [])
        if sessions and sessions[-1]["leave"] is None:
            sessions[-1]["leave"] = now

        # Cleanup movement data
        self._movement_history.pop(uuid_str, None)
        self._last_positions.pop(uuid_str, None)

    def on_move(self, event):
        """Track movement for entropy analysis."""
        player = event.player
        uuid_str = str(player.unique_id)

        try:
            loc = player.location
            current = (loc.x, loc.y, loc.z, loc.yaw, loc.pitch)
        except Exception:
            return

        last = self._last_positions.get(uuid_str)
        self._last_positions[uuid_str] = current

        if last is None:
            return

        # Calculate direction change
        dx = current[0] - last[0]
        dz = current[2] - last[2]
        dyaw = abs(current[3] - last[3]) % 360
        dpitch = abs(current[4] - last[4])

        # Skip if player is standing still
        if abs(dx) < 0.001 and abs(dz) < 0.001:
            return

        # Quantize direction into 8 buckets (N, NE, E, SE, S, SW, W, NW)
        angle = math.atan2(dz, dx)
        bucket = int(((angle + math.pi) / (2 * math.pi)) * 8) % 8

        self._movement_history[uuid_str].append(bucket)

    def on_block_break(self, event):
        """Check if a broken block is a honeypot."""
        if not self._honeypots:
            return

        player = event.player
        block = event.block

        try:
            dim_name = str(player.dimension.name) if hasattr(player, 'dimension') else "overworld"
            pos = (dim_name, int(block.x), int(block.y), int(block.z))
        except Exception:
            return

        if pos in self._honeypots:
            # Honeypot triggered!
            uuid_str = str(player.unique_id)
            self.emit(player, severity=4, evidence={
                "type": "honeypot",
                "block_pos": f"{pos[1]},{pos[2]},{pos[3]}",
                "dimension": pos[0],
                "detail": "Player broke a hidden honeypot block",
            }, action_hint="kick")

            self.alert_admins(
                f"§c{player.name}§e broke a §choneypot block§e at "
                f"({pos[1]}, {pos[2]}, {pos[3]}) in {pos[0]}!"
            )

            # Remove the honeypot since it's been triggered
            self._honeypots.discard(pos)
            self._save_honeypots()

    def check(self):
        """Periodic entropy analysis for all online players."""
        for player in self.plugin.server.online_players:
            uuid_str = str(player.unique_id)

            # Skip admins
            if self.plugin.security.is_level4(player):
                continue

            history = self._movement_history.get(uuid_str)
            if history is None or len(history) < 50:
                continue  # Not enough data yet

            entropy = self._calculate_entropy(history)
            scaled_min = self._scale(MIN_ENTROPY)
            scaled_max = self._scale(MAX_ENTROPY, invert=True)

            if entropy < scaled_min:
                self.emit(player, severity=3, evidence={
                    "type": "low_entropy",
                    "entropy": round(entropy, 3),
                    "threshold": round(scaled_min, 3),
                    "samples": len(history),
                    "detail": "Movement patterns too uniform — possible bot",
                })
                # Reset window to avoid re-flagging immediately
                self._movement_history[uuid_str].clear()

            elif entropy > scaled_max:
                self.emit(player, severity=2, evidence={
                    "type": "high_entropy",
                    "entropy": round(entropy, 3),
                    "threshold": round(scaled_max, 3),
                    "samples": len(history),
                    "detail": "Movement patterns artificially random — possible randomized bot",
                })
                self._movement_history[uuid_str].clear()

    def _check_connection_pattern(self, player, uuid_str: str):
        """Analyze join/leave patterns for bot-like cycling."""
        now = time.time()
        sessions = self._session_log.get(uuid_str, [])

        # Count short sessions in the recent window
        short_count = 0
        for sess in sessions:
            if sess["leave"] is None:
                continue
            duration = sess["leave"] - sess["join"]
            age = now - sess["join"]
            if age <= self._scale(REJOIN_WINDOW) and duration <= SHORT_SESSION_THRESHOLD:
                short_count += 1

        threshold = int(self._scale(MAX_SHORT_SESSIONS, invert=True))
        if short_count >= threshold:
            self.emit(player, severity=3, evidence={
                "type": "connection_cycling",
                "short_sessions": short_count,
                "threshold": threshold,
                "window_s": int(REJOIN_WINDOW),
                "detail": "Rapid join/leave cycling detected — possible bot",
            })

        # Prune old sessions (keep last 20)
        if len(sessions) > 20:
            self._session_log[uuid_str] = sessions[-20:]

    @staticmethod
    def _calculate_entropy(data) -> float:
        """Calculate Shannon entropy of direction bucket distribution."""
        counts = defaultdict(int)
        total = len(data)
        if total == 0:
            return 0.0

        for val in data:
            counts[val] += 1

        entropy = 0.0
        for count in counts.values():
            p = count / total
            if p > 0:
                entropy -= p * math.log2(p)

        return entropy
