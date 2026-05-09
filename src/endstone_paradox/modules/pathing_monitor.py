import math
from endstone.event import PlayerMoveEvent
from endstone_paradox.modules.base import BaseModule

class PathingMonitorModule(BaseModule):
    """Detects Auto-Navigation scripts and superhuman pathing precision."""

    name = "pathingmonitor"
    
    # 0.4 blocks/tick horizontal sprint limit without modifiers
    SPEED_THRESHOLD = 0.4 
    # If yaw delta is exactly 0 for X moves while traveling, it's a bot
    YAW_PRECISION_THRESHOLD = 0.00001
    ROBOTIC_YAW_VIOLATION_THRESHOLD = 40

    def on_start(self):
        self._track = {} # uuid -> {last_yaw, robotic_yaw_count, speed_violations}

    def on_stop(self):
        self._track.clear()

    def on_player_leave(self, player):
        self._track.pop(str(player.unique_id), None)

    def on_player_move(self, event: PlayerMoveEvent):
        if getattr(event, 'is_cancelled', False):
            return

        player = event.player
        if not player or self.plugin.security.is_level4(player):
            return

        from_loc = event.from_location
        to_loc = event.to_location
        
        # Calculate horizontal distance
        dx = to_loc.x - from_loc.x
        dz = to_loc.z - from_loc.z
        h_dist = math.sqrt(dx**2 + dz**2)

        uid = str(player.unique_id)
        data = self._track.setdefault(uid, {
            "last_yaw": from_loc.yaw,
            "robotic_yaw_count": 0,
            "speed_violations": 0
        })

        yaw_delta = abs(to_loc.yaw - data["last_yaw"])

        # Only evaluate pathing if they are actually moving horizontally
        if h_dist > 0.05:
            # 1. Robotic Yaw Check (perfectly straight line over long distance)
            if yaw_delta < self.YAW_PRECISION_THRESHOLD:
                data["robotic_yaw_count"] += 1
            else:
                # Give some leniency, deduct slowly if they turn naturally
                data["robotic_yaw_count"] = max(0, data["robotic_yaw_count"] - 2)

            if data["robotic_yaw_count"] >= self.ROBOTIC_YAW_VIOLATION_THRESHOLD:
                self.emit(player, 6, {
                    "type": "robotic_pathing",
                    "desc": f"Perfectly rigid yaw while moving for {data['robotic_yaw_count']} moves",
                    "yaw_delta": yaw_delta
                }, action_hint="kick")
                data["robotic_yaw_count"] = 0

            # 2. Basic Speed/Distance Check
            # Note: A robust anticheat checks for sprint/jump/ice modifiers.
            # We flag consistently high horizontal displacement without TP
            if h_dist > self.SPEED_THRESHOLD:
                # Filter out likely teleports/elytra/trident
                # For this basic port, just log suspicion
                data["speed_violations"] += 1
                if data["speed_violations"] > 10:
                    self.emit(player, 2, {
                        "type": "pathing_speed",
                        "desc": f"Horizontal speed {h_dist:.2f} blocks/tick",
                        "speed": h_dist
                    })
                    data["speed_violations"] = 0
            else:
                data["speed_violations"] = max(0, data["speed_violations"] - 1)

        data["last_yaw"] = to_loc.yaw
