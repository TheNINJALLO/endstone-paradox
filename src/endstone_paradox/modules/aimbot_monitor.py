import math
from collections import deque
from endstone.event import ActorDamageEvent, PlayerQuitEvent
from endstone_paradox.modules.base import BaseModule

class AimbotMonitorModule(BaseModule):
    """Detects external aim-assist logic (unnatural rotation smoothing)."""

    name = "aimbotmonitor"
    
    ROTATION_PRECISION_THRESHOLD = 0.0001
    VIOLATION_THRESHOLD = 25
    CANCEL_DAMAGE_THRESHOLD = 10
    MIN_TOTAL_DELTA = 0.01

    def on_start(self):
        self._track = {} # uuid -> {last_yaw, last_pitch, deltas (deque), violations}
        self._run_task = True
        self._loop_task()

    def on_stop(self):
        self._run_task = False
        self._track.clear()

    def on_player_leave(self, player):
        self._track.pop(str(player.unique_id), None)

    def _loop_task(self):
        if not self._run_task:
            return

        for player in self.plugin.server.online_players:
            # Exempt L4 staff
            if self.plugin.security.is_level4(player):
                continue
            
            # Note: The TS logic checked for entities in view direction, but Endstone's getEntitiesFromViewDirection
            # might not be available or directly mapped. We'll track rotation variance regardless.
            
            uid = str(player.unique_id)
            rot = player.location
            yaw, pitch = rot.yaw, rot.pitch
            
            data = self._track.get(uid)
            if not data:
                self._track[uid] = {
                    "last_yaw": yaw,
                    "last_pitch": pitch,
                    "deltas": deque(maxlen=15),
                    "violations": 0
                }
                continue
            
            dy = abs(yaw - data["last_yaw"])
            dp = abs(pitch - data["last_pitch"])
            total_delta = dy + dp
            
            if total_delta > self.MIN_TOTAL_DELTA:
                data["deltas"].append(total_delta)
                
                if len(data["deltas"]) == 15:
                    avg = sum(data["deltas"]) / 15
                    variance = sum((b - avg) ** 2 for b in data["deltas"]) / 15
                    
                    if variance < self.ROTATION_PRECISION_THRESHOLD:
                        data["violations"] += 1
                    else:
                        data["violations"] = max(0, data["violations"] - 0.2)
            else:
                data["violations"] = max(0, data["violations"] - 0.5)
                
            if data["violations"] >= self.VIOLATION_THRESHOLD:
                self.emit(player, 4, {
                    "type": "aimbot_smoothing",
                    "desc": "Unnatural rotation smoothing detected",
                    "variance": variance
                }, action_hint="kick")
                data["violations"] = 0
                
            data["last_yaw"] = yaw
            data["last_pitch"] = pitch

        # Schedule next tick (1 tick delay = ~50ms)
        self.plugin.server.scheduler.run_task(self.plugin, self._loop_task, delay=1)

    def on_damage(self, event: ActorDamageEvent):
        """Cancel damage if violations are too high."""
        if getattr(event, 'is_cancelled', False):
            return
            
        damager = event.damage_source.damaging_actor
        if not damager or not hasattr(damager, 'unique_id'):
            return
            
        uid = str(damager.unique_id)
        data = self._track.get(uid)
        
        if data and data["violations"] >= self.CANCEL_DAMAGE_THRESHOLD:
            event.is_cancelled = True
