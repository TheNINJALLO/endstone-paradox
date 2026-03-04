# killaura.py - KillAura detection via dynamic attack pattern analysis
# Uses self-adapting thresholds, proper attacker/victim mapping,
# facing validation via view direction, and latency tolerance.

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
    LATENCY_TOLERANCE = 0.5           # Extra distance allowance for lag

    def on_start(self):
        self._attack_data = {}  # uuid -> deque of timestamps
        self._recent_damage = {}  # uuid -> last_damage_time (for knockback)
        self._target_data = {}  # uuid -> deque of (timestamp, victim_uuid)
        self._apply_sensitivity()

        custom = self.db.get("config", "latency_tolerance")
        if custom is not None:
            self.LATENCY_TOLERANCE = float(custom)

    def _apply_sensitivity(self):
        self.MAX_ATTACKS = max(5, int(self._scale(self.BASE_MAX_ATTACKS_PER_SEC)))
        self.MAX_DISTANCE = self._scale(self.BASE_MAX_ATTACK_DISTANCE) + self.LATENCY_TOLERANCE
        self.MAX_ANGLE = self._scale(self.BASE_MAX_ANGLE)

    def on_stop(self):
        self._attack_data.clear()
        self._recent_damage.clear()
        self._target_data.clear()

    def on_player_leave(self, player):
        uuid_str = str(player.unique_id)
        self._attack_data.pop(uuid_str, None)
        self._recent_damage.pop(uuid_str, None)
        self._target_data.pop(uuid_str, None)

    def on_damage(self, event):
        # The VICTIM is event.actor; the ATTACKER is event.damager
        victim = event.actor
        if victim is None:
            return

        attacker = getattr(event, 'damager', None)
        if attacker is None:
            return

        # Attacker must be a player (has game_mode)
        if not hasattr(attacker, 'game_mode') or not hasattr(attacker, 'unique_id'):
            return

        # Skip L4 admins
        if self.plugin.security.is_level4(attacker):
            return

        uuid_str = str(attacker.unique_id)
        now = time.time()

        attacks = self._attack_data.setdefault(uuid_str, deque(maxlen=self.BUFFER_SIZE))
        attacks.append(now)

        # Count recent attacks (last 1 second)
        recent = [t for t in attacks if now - t <= 1.0]
        attack_rate = float(len(recent))

        # Check 1: Distance check (attacker -> victim)
        distance_ok = self._check_distance(attacker, victim)

        # Check 2: Facing check (is attacker looking at victim?)
        facing_ok = self._check_facing(attacker, victim)

        # Check 3: Attack rate
        rate_ok = attack_rate < self.MAX_ATTACKS

        # Check 4: Pattern consistency (dynamic threshold)
        pattern_ok = not self._is_suspicious_pattern(list(attacks))

        # Record baseline metrics (always, on every hit)
        rate_dev = self.record_baseline(attacker, "combat.attack_rate", attack_rate)

        # Multi-target detection: track unique victims within 0.5s
        victim_uuid = str(victim.unique_id) if hasattr(victim, 'unique_id') else None
        if victim_uuid:
            targets = self._target_data.setdefault(uuid_str, deque())
            targets.append((now, victim_uuid))
            # Prune old entries
            while targets and (now - targets[0][0]) > 0.5:
                targets.popleft()
            # Count unique targets in 0.5s window
            unique_targets = len(set(t[1] for t in targets))
            if unique_targets > 2:
                self.emit(attacker, 4, {
                    "type": "multi_aura",
                    "targets": unique_targets,
                    "window": "0.5s",
                }, action_hint="cancel")
                self._target_data[uuid_str] = deque()

        # Record hit angle baseline (only when facing check passes = normal hits)
        if facing_ok:
            try:
                a_loc = attacker.location
                v_loc = victim.location
                if a_loc and v_loc:
                    d_x = v_loc.x - a_loc.x
                    d_z = v_loc.z - a_loc.z
                    target_yaw = math.degrees(math.atan2(-d_x, d_z))
                    a_yaw = getattr(a_loc, 'yaw', 0) or 0
                    angle = abs(((a_yaw - target_yaw + 180) % 360) - 180)
                    self.record_baseline(attacker, "combat.hit_angle", angle)
            except Exception:
                pass

        # Record timing variance baseline
        if len(attacks) >= 5:
            intervals = [attacks[i] - attacks[i - 1] for i in range(1, len(attacks))]
            if intervals:
                avg_iv = sum(intervals) / len(intervals)
                if avg_iv > 0:
                    variance = sum((iv - avg_iv) ** 2 for iv in intervals) / len(intervals)
                    self.record_baseline(attacker, "combat.timing_variance", variance)

        # Flag if any check fails
        if not distance_ok or not facing_ok or not rate_ok or not pattern_ok:
            try:
                event.cancelled = True
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

            # Escalate if baseline deviation detected
            severity = 3
            evidence = {
                "reasons": ", ".join(reasons),
                "attacks": len(recent),
            }
            if rate_dev and rate_dev.is_deviation:
                severity = 4
                evidence["baseline_deviation"] = rate_dev.z_score

            self.emit(attacker, severity, evidence, action_hint="cancel")
            self._attack_data[uuid_str] = deque(maxlen=self.BUFFER_SIZE)

    def _check_distance(self, attacker, victim):
        """Check if attack distance is within limits."""
        try:
            if victim is None or not hasattr(victim, 'location'):
                return True
            if not hasattr(attacker, 'location'):
                return True
            a_loc = attacker.location
            v_loc = victim.location
            if a_loc is None or v_loc is None:
                return True
            dx = a_loc.x - v_loc.x
            dy = a_loc.y - v_loc.y
            dz = a_loc.z - v_loc.z
            dist = math.sqrt(dx * dx + dy * dy + dz * dz)
            return dist <= self.MAX_DISTANCE
        except Exception:
            return True

    def _check_facing(self, attacker, victim):
        """Check if attacker is facing the target via angle calculation."""
        try:
            if victim is None or not hasattr(victim, 'location'):
                return True
            if not hasattr(attacker, 'location'):
                return True

            a_loc = attacker.location
            v_loc = victim.location
            if a_loc is None or v_loc is None:
                return True

            # Direction to victim
            dx = v_loc.x - a_loc.x
            dz = v_loc.z - a_loc.z
            target_yaw = math.degrees(math.atan2(-dx, dz))

            # Player's yaw
            a_yaw = getattr(a_loc, 'yaw', 0) or 0
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

        intervals = []
        for i in range(1, len(attack_times)):
            intervals.append(attack_times[i] - attack_times[i - 1])

        if len(intervals) < 3:
            return False

        diffs = []
        for i in range(1, len(intervals)):
            diffs.append(intervals[i] - intervals[i - 1])

        if not diffs:
            return False

        avg_diff = sum(abs(d) for d in diffs) / len(diffs)
        variance = sum((abs(d) - avg_diff) ** 2 for d in diffs) / len(diffs)
        std_dev = math.sqrt(variance)

        threshold = avg_diff + 1.5 * std_dev

        all_consistent = all(abs(d) <= max(threshold, 0.008) for d in diffs)

        return all_consistent and avg_diff < 0.02
