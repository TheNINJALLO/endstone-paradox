# criticals.py - Criticals hack detection
# Detects players always landing critical hits without actually falling.

import time
from collections import deque
from endstone_paradox.modules.base import BaseModule


class CriticalsModule(BaseModule):
    """Detects criticals hack.

    A legitimate critical hit requires the player to be:
    - Not on the ground
    - Falling (negative Y velocity)
    - Not in water, on ladder, or in a vehicle

    Criticals hacks fake the falling state. We detect by checking if
    the player's Y position has been consistently stable (not actually
    falling) yet they're dealing critical-level damage.

    Tracking approach: record Y positions around each hit.  If the Y
    hasn't changed but damage is critical (1.5x), flag.
    """

    name = "criticals"

    CRIT_DAMAGE_MULTIPLIER = 1.4  # damage ratio above normal that suggests crit
    Y_CHANGE_REQUIRED = 0.1       # minimum Y drop expected for legit crit
    SAMPLE_WINDOW = 0.5           # seconds of Y history to check
    FLAGS_REQUIRED = 5            # consecutive suspicious crits before flag

    def on_start(self):
        self._player_data = {}  # uuid -> {y_history: deque, crit_flags}

    def on_stop(self):
        self._player_data.clear()

    def on_player_leave(self, player):
        self._player_data.pop(str(player.unique_id), None)

    @property
    def check_interval(self) -> int:
        return 5  # record Y every 0.25s

    def check(self):
        """Record Y positions for all players."""
        now = time.time()
        for player in self.plugin.server.online_players:
            try:
                uuid_str = str(player.unique_id)
                loc = player.location
                data = self._player_data.setdefault(uuid_str, {
                    "y_history": deque(maxlen=20),
                    "crit_flags": 0,
                })
                data["y_history"].append((now, loc.y))
            except Exception:
                pass

    def on_damage(self, event):
        """Check if an attack is a suspicious critical hit."""
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
        if data is None or len(data["y_history"]) < 4:
            return

        now = time.time()

        # Check if the player was actually falling
        # Look at Y history over the last 0.5s
        recent_y = [y for t, y in data["y_history"] if now - t < self.SAMPLE_WINDOW]
        if len(recent_y) < 2:
            return

        y_change = max(recent_y) - min(recent_y)

        # If attacker is on ground AND is not actually falling, yet hitting
        if attacker.is_on_ground and y_change < self.Y_CHANGE_REQUIRED:
            # Quick successive ground-level hits with no real jumping = suspicious
            # But only flag if they're hitting WHILE on ground (legit crits need airborne)
            data["crit_flags"] += 1
            if data["crit_flags"] >= self.FLAGS_REQUIRED:
                self.emit(attacker, 3, {
                    "type": "criticals",
                    "y_change": f"{y_change:.3f}",
                    "flags": data["crit_flags"],
                })
                data["crit_flags"] = 0
        else:
            data["crit_flags"] = max(0, data["crit_flags"] - 1)
