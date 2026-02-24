"""
Paradox AntiCheat - KillAura Detection Module

Detects KillAura by analyzing attack frequency, timing consistency,
and attacker facing angle relative to the victim.
"""

import math
import time
from collections import deque
from endstone_paradox.modules.base import BaseModule


class KillAuraModule(BaseModule):
    """Detects KillAura hacks via statistical attack pattern analysis."""

    name = "killaura"

    # Detection thresholds
    MIN_ATTACKS = 5          # Minimum attacks to analyze
    TIME_WINDOW = 3.0        # Seconds to track attacks
    MIN_STD_DEV = 0.02       # Minimum standard deviation (too consistent = bot)
    MAX_ANGLE = 90.0         # Max angle between facing and target (degrees)

    def on_start(self):
        self._attack_data = {}  # UUID -> deque of timestamps

    def on_stop(self):
        self._attack_data.clear()

    def on_player_leave(self, player):
        self._attack_data.pop(str(player.unique_id), None)

    def on_damage(self, event):
        """Analyze attack patterns on damage events."""
        # Only process entity-on-entity attacks
        actor = event.actor
        if actor is None or not hasattr(actor, 'unique_id'):
            return

        # Check if attacker is a player
        if not hasattr(actor, 'game_mode'):
            return

        # Skip Level 4 players
        if self.plugin.security.is_level4(actor):
            return

        uuid_str = str(actor.unique_id)
        now = time.time()

        # Track attack timestamps
        attacks = self._attack_data.setdefault(uuid_str, deque())
        attacks.append(now)

        # Remove old attacks outside the window
        while attacks and (now - attacks[0]) > self.TIME_WINDOW:
            attacks.popleft()

        if len(attacks) < self.MIN_ATTACKS:
            return

        # Calculate intervals between attacks
        intervals = []
        attack_list = list(attacks)
        for i in range(1, len(attack_list)):
            intervals.append(attack_list[i] - attack_list[i - 1])

        if not intervals:
            return

        # Statistical analysis
        avg_interval = sum(intervals) / len(intervals)
        variance = sum((i - avg_interval) ** 2 for i in intervals) / len(intervals)
        std_dev = math.sqrt(variance)

        # Check facing angle
        angle_check = self._check_facing_angle(actor, event)

        # KillAura detection: too-consistent timing + bad angle
        if std_dev < self.MIN_STD_DEV or not angle_check:
            # Restore victim health
            victim = event.actor  # The damaged entity
            try:
                damage = event.damage
                if hasattr(event, 'actor') and event.actor != actor:
                    victim = event.actor
                # Cancel the damage by healing
                event.is_cancelled = True
            except Exception:
                pass

            self.alert_admins(
                f"§c{actor.name}§e flagged for KillAura "
                f"(σ={std_dev:.4f}, attacks={len(attacks)})"
            )
            self._attack_data[uuid_str].clear()

    def _check_facing_angle(self, attacker, event) -> bool:
        """Check if the attacker is roughly facing the victim."""
        try:
            a_loc = attacker.location
            # Get the damaged entity
            # In Endstone, ActorDamageEvent has .actor (the damaged entity)
            # We need the victim, which is event.actor
            v_loc = event.actor.location if event.actor != attacker else None
            if v_loc is None:
                return True  # Can't check, assume OK

            # Calculate direction to victim
            dx = v_loc.x - a_loc.x
            dz = v_loc.z - a_loc.z
            target_yaw = math.degrees(math.atan2(-dx, dz))

            # Get attacker's yaw
            a_yaw = a_loc.yaw if hasattr(a_loc, 'yaw') else 0

            # Normalize angle difference
            angle_diff = abs(((a_yaw - target_yaw + 180) % 360) - 180)

            return angle_diff <= self.MAX_ANGLE
        except Exception:
            return True  # Can't check, assume OK
