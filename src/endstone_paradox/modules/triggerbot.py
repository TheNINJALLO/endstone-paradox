# triggerbot.py - TriggerBot detection
# Detects automatic attacks when crosshair enters a target's hitbox.

import time
from collections import deque
from endstone_paradox.modules.base import BaseModule


class TriggerBotModule(BaseModule):
    """Detects triggerbot (automatic attack on target acquisition).

    Tracks the time between a player first looking at a target
    (rotation toward entity) and the attack. Humans have variable
    reaction times (100-300ms). TriggerBots consistently attack
    within 1-2 ticks (~50-100ms) of acquiring a target.

    Detection: track rotation → attack timing. If >5 consecutive
    attacks happen within 100ms of a rotation change toward the target,
    flag as triggerbot.
    """

    name = "triggerbot"

    REACTION_THRESHOLD = 0.10  # 100ms — below this is inhuman
    WINDOW_SIZE = 10           # attacks to analyze
    FLAGS_REQUIRED = 4         # suspicious attacks in window before flag

    def on_start(self):
        self._player_data = {}  # uuid -> {last_rotation_change, attack_timings: deque}

    def on_stop(self):
        self._player_data.clear()

    def on_player_leave(self, player):
        self._player_data.pop(str(player.unique_id), None)

    @property
    def check_interval(self) -> int:
        return 2  # 0.1 seconds — track rotation precisely

    def check(self):
        """Track rotation changes for all players."""
        now = time.time()
        for player in self.plugin.server.online_players:
            try:
                uuid_str = str(player.unique_id)
                loc = player.location
                yaw = loc.yaw if hasattr(loc, 'yaw') else 0
                pitch = loc.pitch if hasattr(loc, 'pitch') else 0

                data = self._player_data.setdefault(uuid_str, {
                    "last_yaw": yaw,
                    "last_pitch": pitch,
                    "last_rotation_change": 0,
                    "attack_timings": deque(maxlen=self.WINDOW_SIZE),
                })

                # Detect rotation change
                d_yaw = abs(((yaw - data["last_yaw"] + 180) % 360) - 180)
                d_pitch = abs(pitch - data["last_pitch"])

                if d_yaw > 2.0 or d_pitch > 2.0:  # meaningful rotation change
                    data["last_rotation_change"] = now

                data["last_yaw"] = yaw
                data["last_pitch"] = pitch
            except Exception:
                pass

    def on_damage(self, event):
        """Check time between last rotation change and this attack."""
        attacker = getattr(event, 'damager', None)
        if attacker is None or not hasattr(attacker, 'unique_id'):
            return
        if not hasattr(attacker, 'game_mode'):
            return
        if self.plugin.security.is_level4(attacker):
            return

        from endstone import GameMode
        if attacker.game_mode in (GameMode.CREATIVE, GameMode.SPECTATOR):
            return

        uuid_str = str(attacker.unique_id)
        data = self._player_data.get(uuid_str)
        if data is None:
            return

        now = time.time()
        rotation_to_attack = now - data["last_rotation_change"]

        # Only analyze if rotation change happened recently (within 1s)
        if rotation_to_attack > 1.0:
            return

        data["attack_timings"].append(rotation_to_attack)

        # Analyze when we have enough data
        if len(data["attack_timings"]) >= self.WINDOW_SIZE:
            fast_attacks = sum(
                1 for t in data["attack_timings"] if t < self.REACTION_THRESHOLD
            )
            if fast_attacks >= self.FLAGS_REQUIRED:
                avg_timing = sum(data["attack_timings"]) / len(data["attack_timings"])
                self.emit(attacker, 4, {
                    "type": "triggerbot",
                    "fast_attacks": fast_attacks,
                    "avg_reaction": f"{avg_timing*1000:.0f}ms",
                    "threshold": f"{self.REACTION_THRESHOLD*1000:.0f}ms",
                })
                data["attack_timings"].clear()
