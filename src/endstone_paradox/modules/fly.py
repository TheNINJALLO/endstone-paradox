"""
Paradox AntiCheat - Fly Detection Module

Monitors player movement to detect illicit flying. Uses ground tracking,
velocity analysis, PlayerJumpEvent flags, and surrounding block checks.
Teleports offenders back to their last known grounded position.
"""

import math
from endstone import GameMode
from endstone_paradox.modules.base import BaseModule


class FlyModule(BaseModule):
    """Detects illegal flying and airborne movement."""

    name = "fly"
    check_interval = 20  # Check every 1 second (20 ticks)

    def on_start(self):
        self._player_data = {}  # UUID -> {landing: Location, hover_time: int, trident_used: bool}

    def on_stop(self):
        self._player_data.clear()

    def on_player_leave(self, player):
        self._player_data.pop(str(player.unique_id), None)

    def check(self):
        """Periodic fly check across all players."""
        for player in self.plugin.server.online_players:
            try:
                self._check_player(player)
            except Exception:
                pass

    def _check_player(self, player):
        uuid_str = str(player.unique_id)

        # Skip exempt players
        if player.game_mode in (GameMode.CREATIVE, GameMode.SPECTATOR):
            return
        if self.plugin.security.is_level4(player):
            return

        # Skip if gliding (elytra), in water, or climbing
        if player.is_gliding or player.is_in_water:
            return
        if self.plugin.is_player_climbing(player):
            return

        # Get or create player data
        data = self._player_data.setdefault(uuid_str, {
            "landing": None,
            "hover_time": 0,
            "trident_used": False,
        })

        # Check trident usage exemption
        if data["trident_used"]:
            data["trident_used"] = False
            return

        loc = player.location

        # Record landing position when on ground
        if player.is_on_ground:
            data["landing"] = loc
            data["hover_time"] = 0
            return

        # Skip if player recently jumped (legitimate air time)
        if self.plugin.is_player_jumping(player):
            return

        # Get velocity for analysis
        vel = player.velocity
        h_speed = math.sqrt(vel.x ** 2 + vel.z ** 2)
        v_threshold = 0.5   # Generous to avoid flagging normal jumps/falls
        h_threshold = 0.5   # Generous to avoid flagging normal sprinting
        hover_threshold = 5  # 5 seconds at 1-second interval

        # Check for suspicious airborne movement
        is_suspicious = (
            (player.is_flying and not player.is_on_ground) or
            (abs(vel.y) >= v_threshold or h_speed >= h_threshold)
        )

        if is_suspicious and not player.is_on_ground:
            data["hover_time"] += 1

            if data["hover_time"] >= hover_threshold:
                # Teleport back to last landing
                landing = data.get("landing")
                if landing:
                    player.teleport(landing)
                    self.alert_admins(
                        f"§c{player.name}§e was detected flying and teleported back."
                    )
                data["hover_time"] = 0
        else:
            data["hover_time"] = max(0, data["hover_time"] - 1)

    def set_trident_used(self, player):
        """Mark a player as having used a trident (exempt from fly check)."""
        uuid_str = str(player.unique_id)
        data = self._player_data.get(uuid_str)
        if data:
            data["trident_used"] = True
