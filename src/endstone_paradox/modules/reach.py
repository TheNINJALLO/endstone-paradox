"""
Paradox AntiCheat - Reach Detection Module

Detects reach hacks by tracking player movement history and using
interpolation to estimate positions at the time of a hit.
"""

import math
import time
from collections import deque
from endstone_paradox.modules.base import BaseModule


class ReachModule(BaseModule):
    """Detects reach hacks via distance analysis with movement interpolation."""

    name = "reach"
    check_interval = 5  # Track positions every 0.25 seconds

    MAX_ATTACK_DISTANCE = 3.5   # Blocks (with some tolerance)
    HISTORY_SIZE = 20           # Number of position samples to keep

    def on_start(self):
        self._move_history = {}  # UUID -> deque of (time, x, y, z, vx, vy, vz)

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
                history = self._move_history.setdefault(uuid_str, deque(maxlen=self.HISTORY_SIZE))
                history.append((now, loc.x, loc.y, loc.z, vel.x, vel.y, vel.z))
            except Exception:
                pass

    def on_damage(self, event):
        """Check attack distance on damage events."""
        actor = event.actor
        if actor is None or not hasattr(actor, 'unique_id'):
            return
        if not hasattr(actor, 'game_mode'):
            return
        if self.plugin.security.is_level4(actor):
            return

        # Get the damaged entity's location
        try:
            victim = event.actor
            if victim is None or victim == actor:
                return

            v_loc = victim.location
            a_uuid = str(actor.unique_id)

            # Get attacker's interpolated position at attack time
            a_loc = self._get_estimated_position(a_uuid, time.time())
            if a_loc is None:
                return

            # Calculate 3D distance
            dx = a_loc[0] - v_loc.x
            dy = a_loc[1] - v_loc.y
            dz = a_loc[2] - v_loc.z
            distance = math.sqrt(dx * dx + dy * dy + dz * dz)

            if distance > self.MAX_ATTACK_DISTANCE:
                # Cancel the damage
                event.is_cancelled = True
                self.alert_admins(
                    f"§c{actor.name}§e flagged for Reach "
                    f"(dist={distance:.2f}, max={self.MAX_ATTACK_DISTANCE})"
                )
        except Exception:
            pass

    def _get_estimated_position(self, uuid_str: str, target_time: float):
        """Estimate player position at a given time using linear interpolation."""
        history = self._move_history.get(uuid_str)
        if not history or len(history) < 2:
            return None

        # Find the two samples bracketing the target time
        history_list = list(history)
        for i in range(len(history_list) - 1):
            t0, x0, y0, z0, *_ = history_list[i]
            t1, x1, y1, z1, *_ = history_list[i + 1]
            if t0 <= target_time <= t1:
                if t1 == t0:
                    return (x0, y0, z0)
                alpha = (target_time - t0) / (t1 - t0)
                return (
                    x0 + alpha * (x1 - x0),
                    y0 + alpha * (y1 - y0),
                    z0 + alpha * (z1 - z0),
                )

        # If target_time is after our last sample, use the latest position
        last = history_list[-1]
        return (last[1], last[2], last[3])
