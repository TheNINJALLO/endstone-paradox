# killaura.py - KillAura detection via dynamic attack pattern analysis
# Uses self-adapting thresholds based on interval differences and
# proper facing validation via view direction dot product.

import math
import time
from collections import deque
from endstone_paradox.modules.base import BaseModule


class KillAuraModule(BaseModule):
    name = "killaura"

    # Base tuning constants (at sensitivity 5)
    BASE_MAX_ATTACKS_PER_SEC = 14     # Max attacks in 1 second
    BASE_MAX_ATTACK_DISTANCE = 4.5    # Max legitimate hit distance
    BASE_MAX_ANGLE = 60.0             # Max angle between view and target
    BUFFER_SIZE = 20                   # Attack time buffer

    def on_start(self):
        self._attack_data = {}  # uuid -> deque of timestamps (in ticks/time)
        self._apply_sensitivity()

    def _apply_sensitivity(self):
        self.MAX_ATTACKS = max(5, int(self._scale(self.BASE_MAX_ATTACKS_PER_SEC)))
        self.MAX_DISTANCE = self._scale(self.BASE_MAX_ATTACK_DISTANCE)
        self.MAX_ANGLE = self._scale(self.BASE_MAX_ANGLE)

    def on_stop(self):
        self._attack_data.clear()

    def on_player_leave(self, player):
        self._attack_data.pop(str(player.unique_id), None)

    def on_damage(self, event):
        actor = event.actor
        if actor is None or not hasattr(actor, 'unique_id'):
            return
        if not hasattr(actor, 'game_mode'):
            return
        if self.plugin.security.is_level4(actor):
            return

        uuid_str = str(actor.unique_id)
        now = time.time()

        attacks = self._attack_data.setdefault(uuid_str, deque(maxlen=self.BUFFER_SIZE))
        attacks.append(now)

        # Count recent attacks (last 1 second)
        recent = [t for t in attacks if now - t <= 1.0]

        # Check 1: Distance check
        distance_ok = self._check_distance(actor, event)

        # Check 2: Facing check
        facing_ok = self._check_facing(actor, event)

        # Check 3: Attack rate
        rate_ok = len(recent) < self.MAX_ATTACKS

        # Check 4: Pattern consistency (dynamic threshold)
        pattern_ok = not self._is_suspicious_pattern(list(attacks))

        # Flag if any check fails
        if not distance_ok or not facing_ok or not rate_ok or not pattern_ok:
            try:
                event.is_cancelled = True
            except Exception:
                pass

            reasons = []
            if not distance_ok:
                reasons.append("dist")
            if not facing_ok:
                reasons.append("angle")
            if not rate_ok:
                reasons.append(f"rate={len(recent)}/s")
            if not pattern_ok:
                reasons.append("pattern")

            self.alert_admins(
                f"§c{actor.name}§e flagged for KillAura "
                f"({', '.join(reasons)})"
            )
            self._attack_data[uuid_str] = deque(maxlen=self.BUFFER_SIZE)

    def _check_distance(self, attacker, event):
        """Check if attack distance is within limits."""
        try:
            victim = event.actor if event.actor != attacker else None
            if victim is None:
                return True
            a_loc = attacker.location
            v_loc = victim.location
            dx = a_loc.x - v_loc.x
            dy = a_loc.y - v_loc.y
            dz = a_loc.z - v_loc.z
            dist = math.sqrt(dx * dx + dy * dy + dz * dz)
            return dist <= self.MAX_DISTANCE
        except Exception:
            return True

    def _check_facing(self, attacker, event):
        """Check if attacker is facing the target via angle calculation."""
        try:
            victim = event.actor if event.actor != attacker else None
            if victim is None:
                return True

            a_loc = attacker.location
            v_loc = victim.location

            # Direction to victim
            dx = v_loc.x - a_loc.x
            dz = v_loc.z - a_loc.z
            target_yaw = math.degrees(math.atan2(-dx, dz))

            # Player's yaw
            a_yaw = a_loc.yaw if hasattr(a_loc, 'yaw') else 0
            angle_diff = abs(((a_yaw - target_yaw + 180) % 360) - 180)

            return angle_diff <= self.MAX_ANGLE
        except Exception:
            return True

    def _is_suspicious_pattern(self, attack_times):
        """
        Detect suspiciously consistent attack timing using dynamic thresholds.
        Computes interval differences and checks if they're too uniform.
        """
        if len(attack_times) < 5:
            return False

        # Compute intervals
        intervals = []
        for i in range(1, len(attack_times)):
            intervals.append(attack_times[i] - attack_times[i - 1])

        if len(intervals) < 3:
            return False

        # Compute differences between consecutive intervals
        diffs = []
        for i in range(1, len(intervals)):
            diffs.append(intervals[i] - intervals[i - 1])

        if not diffs:
            return False

        # Dynamic threshold = avg_diff + 1.5 * stddev
        avg_diff = sum(abs(d) for d in diffs) / len(diffs)
        variance = sum((abs(d) - avg_diff) ** 2 for d in diffs) / len(diffs)
        std_dev = math.sqrt(variance)

        threshold = avg_diff + 1.5 * std_dev

        # If all diffs are within the threshold, timing is too consistent
        all_consistent = all(abs(d) <= max(threshold, 0.008) for d in diffs)

        return all_consistent and avg_diff < 0.02  # Very tight, robotic timing
