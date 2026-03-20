# antikb.py - Anti-Knockback detection
# Detects players not taking knockback after being hit.

import time
import math
from endstone_paradox.modules.base import BaseModule


class AntiKBModule(BaseModule):
    """Detects anti-knockback (velocity hack).

    After a player takes damage from an attacker, they should move
    away from the attacker within a short window.  If they don't
    move at all (or move toward the attacker), flag as AntiKB.
    """

    name = "antikb"

    KB_CHECK_DELAY = 0.15   # seconds after hit to check position (3 ticks)
    MIN_KB_DISTANCE = 0.1   # minimum horizontal displacement expected
    FLAGS_REQUIRED = 3       # consecutive AntiKB detections before flag

    def on_start(self):
        self._pending_checks = {}  # uuid -> {hit_time, hit_pos, attacker_pos}
        self._flags = {}  # uuid -> count

    def on_stop(self):
        self._pending_checks.clear()
        self._flags.clear()

    def on_player_leave(self, player):
        uuid_str = str(player.unique_id)
        self._pending_checks.pop(uuid_str, None)
        self._flags.pop(uuid_str, None)

    def on_damage(self, event):
        """Track when a player is hit by another entity."""
        victim = event.actor
        attacker = getattr(event, 'damager', None)

        if victim is None or attacker is None:
            return
        if not hasattr(victim, 'game_mode') or not hasattr(victim, 'unique_id'):
            return
        if not hasattr(attacker, 'unique_id'):
            return
        # Only care about player victims
        if self.plugin.security.is_level4(victim):
            return
        # Don't check self-damage
        if str(victim.unique_id) == str(attacker.unique_id):
            return

        from endstone import GameMode
        if victim.game_mode in (GameMode.CREATIVE, GameMode.SPECTATOR):
            return

        uuid_str = str(victim.unique_id)
        loc = victim.location

        self._pending_checks[uuid_str] = {
            "hit_time": time.time(),
            "hit_pos": (loc.x, loc.z),
            "checked": False,
        }

    @property
    def check_interval(self) -> int:
        return 4  # check every 0.2 seconds for precision

    def check(self):
        """Check pending KB verifications."""
        now = time.time()
        expired = []

        for uuid_str, data in self._pending_checks.items():
            if data["checked"]:
                expired.append(uuid_str)
                continue

            if now - data["hit_time"] < self.KB_CHECK_DELAY:
                continue  # too early

            if now - data["hit_time"] > 1.0:
                expired.append(uuid_str)  # too late, skip
                continue

            # Find the player
            player = None
            for p in self.plugin.server.online_players:
                if str(p.unique_id) == uuid_str:
                    player = p
                    break

            if player is None:
                expired.append(uuid_str)
                continue

            data["checked"] = True

            loc = player.location
            cur = (loc.x, loc.z)
            prev = data["hit_pos"]

            dx = cur[0] - prev[0]
            dz = cur[1] - prev[1]
            displacement = math.sqrt(dx*dx + dz*dz)

            if displacement < self.MIN_KB_DISTANCE:
                # Player didn't move — AntiKB detected
                count = self._flags.get(uuid_str, 0) + 1
                self._flags[uuid_str] = count

                if count >= self.FLAGS_REQUIRED:
                    self.emit(player, 4, {
                        "type": "antikb",
                        "desc": f"Didn't move after being hit {count} times (displacement {displacement:.3f}b)",
                        "displacement": f"{displacement:.3f}",
                        "expected_min": f"{self.MIN_KB_DISTANCE}",
                        "hits": count,
                    }, action_hint="cancel")
                    self._flags[uuid_str] = 0
            else:
                self._flags[uuid_str] = max(0, self._flags.get(uuid_str, 0) - 1)

        for k in expired:
            self._pending_checks.pop(k, None)
