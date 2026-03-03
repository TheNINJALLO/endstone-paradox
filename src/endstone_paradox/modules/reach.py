# reach.py - Reach detection via Catmull-Rom cubic interpolation
# Tracks position history and uses cubic interpolation to estimate
# player positions at the moment of attack for accurate distance checks.
# Fixed: uses event.damager as attacker, event.actor as victim.

import math
import time
from collections import deque
from endstone_paradox.modules.base import BaseModule


class ReachModule(BaseModule):
    """Detects reach hacks via Catmull-Rom interpolated distance analysis."""

    name = "reach"
    check_interval = 1  # Track positions every tick (50ms)

    BASE_MAX_ATTACK_DISTANCE = 4.5   # Blocks — vanilla ~3, generous for latency
    HISTORY_SIZE = 10                 # Position samples to keep
    LATENCY_TOLERANCE = 0.5          # Extra distance for lag

    def on_start(self):
        self._move_history = {}  # UUID -> deque of (time, x, y, z, vx, vy, vz)
        self._apply_sensitivity()

        custom = self.db.get("config", "latency_tolerance")
        if custom is not None:
            self.LATENCY_TOLERANCE = float(custom)

    def _apply_sensitivity(self):
        self.MAX_ATTACK_DISTANCE = self._scale(self.BASE_MAX_ATTACK_DISTANCE) + self.LATENCY_TOLERANCE

    def on_stop(self):
        self._move_history.clear()

    def on_player_leave(self, player):
        self._move_history.pop(str(player.unique_id), None)

    def check(self):
        """Record position snapshots for all players."""
        now = time.time()
        for player in self.plugin.server.online_players:
            try:
                uuid_str = str(player.unique_id)
                loc = player.location
                vel = player.velocity
                if loc is None or vel is None:
                    continue
                history = self._move_history.setdefault(
                    uuid_str, deque(maxlen=self.HISTORY_SIZE)
                )
                history.append((now, loc.x, loc.y, loc.z, vel.x, vel.y, vel.z))
            except Exception:
                pass

    def on_damage(self, event):
        """Check attack distance on damage events."""
        # VICTIM = event.actor, ATTACKER = event.damager
        victim = event.actor
        if victim is None:
            return

        attacker = getattr(event, 'damager', None)
        if attacker is None:
            return

        # Attacker must be a player
        if not hasattr(attacker, 'game_mode') or not hasattr(attacker, 'unique_id'):
            return

        if self.plugin.security.is_level4(attacker):
            return

        try:
            if not hasattr(victim, 'location') or victim.location is None:
                return

            a_uuid = str(attacker.unique_id)
            v_uuid = str(victim.unique_id) if hasattr(victim, 'unique_id') else None
            v_loc = victim.location

            now = time.time()

            # Get interpolated position for the ATTACKER
            a_pos = self._estimate_position_cubic(a_uuid, now - 0.05)
            if a_pos is None:
                return

            # Get interpolated position for the victim (if tracked)
            if v_uuid:
                v_pos = self._estimate_position_cubic(v_uuid, now - 0.05)
                if v_pos:
                    vx, vy, vz = v_pos
                else:
                    vx, vy, vz = v_loc.x, v_loc.y, v_loc.z
            else:
                vx, vy, vz = v_loc.x, v_loc.y, v_loc.z

            # Calculate 3D distance
            dx = a_pos[0] - vx
            dy = a_pos[1] - vy
            dz = a_pos[2] - vz
            distance = math.sqrt(dx * dx + dy * dy + dz * dz)

            if distance > self.MAX_ATTACK_DISTANCE:
                try:
                    event.cancelled = True
                except Exception:
                    pass
                self.emit(attacker, 3, {
                    "dist": f"{distance:.2f}",
                    "max": f"{self.MAX_ATTACK_DISTANCE:.1f}",
                }, action_hint="cancel")
        except Exception:
            pass

    # ─── Catmull-Rom Cubic Interpolation ─────────────────

    def _estimate_position_cubic(self, uuid_str, target_time):
        """
        Estimate player position using Catmull-Rom cubic interpolation.
        Requires at least 4 position samples for smooth interpolation.
        Falls back to linear if only 2-3 samples available.
        """
        history = self._move_history.get(uuid_str)
        if not history or len(history) < 2:
            return None

        h = list(history)

        # If we have 4+ samples, use Catmull-Rom
        if len(h) >= 4:
            for i in range(1, len(h) - 2):
                t1 = h[i][0]
                t2 = h[i + 1][0]
                if t1 <= target_time <= t2:
                    if t2 == t1:
                        return (h[i][1], h[i][2], h[i][3])
                    alpha = (target_time - t1) / (t2 - t1)
                    return self._catmull_rom(
                        (h[i - 1][1], h[i - 1][2], h[i - 1][3]),
                        (h[i][1], h[i][2], h[i][3]),
                        (h[i + 1][1], h[i + 1][2], h[i + 1][3]),
                        (h[i + 2][1], h[i + 2][2], h[i + 2][3]),
                        alpha
                    )

        # Fallback: linear interpolation
        for i in range(len(h) - 1):
            t0, x0, y0, z0 = h[i][0], h[i][1], h[i][2], h[i][3]
            t1, x1, y1, z1 = h[i + 1][0], h[i + 1][1], h[i + 1][2], h[i + 1][3]
            if t0 <= target_time <= t1:
                if t1 == t0:
                    return (x0, y0, z0)
                alpha = (target_time - t0) / (t1 - t0)
                return (
                    x0 + alpha * (x1 - x0),
                    y0 + alpha * (y1 - y0),
                    z0 + alpha * (z1 - z0),
                )

        last = h[-1]
        return (last[1], last[2], last[3])

    @staticmethod
    def _catmull_rom(p0, p1, p2, p3, t):
        """Catmull-Rom cubic interpolation between p1 and p2."""
        t2 = t * t
        t3 = t2 * t
        return (
            0.5 * (2 * p1[0] + (-p0[0] + p2[0]) * t +
                   (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 +
                   (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3),
            0.5 * (2 * p1[1] + (-p0[1] + p2[1]) * t +
                   (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 +
                   (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3),
            0.5 * (2 * p1[2] + (-p0[2] + p2[2]) * t +
                   (2 * p0[2] - 5 * p1[2] + 4 * p2[2] - p3[2]) * t2 +
                   (-p0[2] + 3 * p1[2] - 3 * p2[2] + p3[2]) * t3),
        )
