# killaura.py - KillAura detection via attack timing + facing analysis

import math
import time
from collections import deque
from endstone_paradox.modules.base import BaseModule


class KillAuraModule(BaseModule):
    name = "killaura"

    # Base tuning constants (at sensitivity 5)
    BASE_MIN_ATTACKS = 8        # need enough data to analyze
    BASE_TIME_WINDOW = 5.0      # seconds
    BASE_MIN_STD_DEV = 0.008    # only flags truly robotic timing
    BASE_MAX_ANGLE = 120.0      # bedrock hit detection is pretty generous

    def on_start(self):
        self._attack_data = {}  # uuid -> deque of timestamps
        self._apply_sensitivity()

    def _apply_sensitivity(self):
        self.MIN_ATTACKS = max(3, int(self._scale(self.BASE_MIN_ATTACKS)))
        self.TIME_WINDOW = self.BASE_TIME_WINDOW
        self.MIN_STD_DEV = self._scale(self.BASE_MIN_STD_DEV)
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

        attacks = self._attack_data.setdefault(uuid_str, deque())
        attacks.append(now)

        # prune old entries
        while attacks and (now - attacks[0]) > self.TIME_WINDOW:
            attacks.popleft()

        if len(attacks) < self.MIN_ATTACKS:
            return

        # calculate timing intervals
        intervals = []
        attack_list = list(attacks)
        for i in range(1, len(attack_list)):
            intervals.append(attack_list[i] - attack_list[i - 1])

        if not intervals:
            return

        avg_interval = sum(intervals) / len(intervals)
        variance = sum((i - avg_interval) ** 2 for i in intervals) / len(intervals)
        std_dev = math.sqrt(variance)

        angle_check = self._check_facing_angle(actor, event)

        # flag if timing is too consistent or angle is way off
        if std_dev < self.MIN_STD_DEV or not angle_check:
            try:
                event.is_cancelled = True
            except Exception:
                pass

            self.alert_admins(
                f"§c{actor.name}§e flagged for KillAura "
                f"(σ={std_dev:.4f}, attacks={len(attacks)})"
            )
            self._attack_data[uuid_str].clear()

    def _check_facing_angle(self, attacker, event) -> bool:
        """Returns True if attacker is roughly facing the victim."""
        try:
            a_loc = attacker.location
            v_loc = event.actor.location if event.actor != attacker else None
            if v_loc is None:
                return True  # can't check

            dx = v_loc.x - a_loc.x
            dz = v_loc.z - a_loc.z
            target_yaw = math.degrees(math.atan2(-dx, dz))

            a_yaw = a_loc.yaw if hasattr(a_loc, 'yaw') else 0
            angle_diff = abs(((a_yaw - target_yaw + 180) % 360) - 180)

            return angle_diff <= self.MAX_ANGLE
        except Exception:
            return True
