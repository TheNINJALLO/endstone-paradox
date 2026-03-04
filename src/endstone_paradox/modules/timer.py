# timer.py - Timer Hack detection
# Detects game speed manipulation by tracking PlayerAuthInputPacket frequency.

import time
from collections import deque
from endstone_paradox.modules.base import BaseModule


class TimerModule(BaseModule):
    """Detects timer hacks (game speed manipulation).

    Minecraft sends PlayerAuthInputPacket at ~20 ticks/second.
    Timer hacks speed up the game clock, causing packets to arrive faster.
    - Normal:     ~20 packets/s
    - Timer 1.5x: ~30 packets/s
    - Slow timer: ~15 packets/s (also exploitable)
    """

    name = "timer"

    MAX_PACKETS_PER_SEC = 23   # generous (allows some network jitter)
    MIN_PACKETS_PER_SEC = 15   # slow-timer floor
    WINDOW_SIZE = 2.0          # analysis window in seconds
    FLAGS_REQUIRED = 4         # consecutive windows before flag

    def on_start(self):
        self._player_data = {}  # uuid -> {timestamps: deque, fast_flags, slow_flags}

    def on_stop(self):
        self._player_data.clear()

    def on_player_leave(self, player):
        self._player_data.pop(str(player.unique_id), None)

    def on_packet(self, event):
        """Track PlayerAuthInputPacket frequency."""
        pkt = event.packet
        pkt_type = type(pkt).__name__

        if pkt_type != "PlayerAuthInputPacket":
            return

        player = event.player if hasattr(event, 'player') else None
        if player is None:
            return
        if self.plugin.security.is_level4(player):
            return

        uuid_str = str(player.unique_id)
        now = time.time()

        data = self._player_data.setdefault(uuid_str, {
            "timestamps": deque(),
            "fast_flags": 0,
            "slow_flags": 0,
            "last_check": now,
        })

        data["timestamps"].append(now)

        # Only analyze every WINDOW_SIZE seconds
        if now - data["last_check"] < self.WINDOW_SIZE:
            return

        data["last_check"] = now

        # Count packets in window
        ts = data["timestamps"]
        while ts and (now - ts[0]) > self.WINDOW_SIZE:
            ts.popleft()

        count = len(ts)
        pps = count / self.WINDOW_SIZE  # packets per second

        # Fast timer detection
        if pps > self.MAX_PACKETS_PER_SEC:
            data["fast_flags"] += 1
            if data["fast_flags"] >= self.FLAGS_REQUIRED:
                self.emit(player, 4, {
                    "type": "timer_fast",
                    "pps": f"{pps:.1f}",
                    "max": self.MAX_PACKETS_PER_SEC,
                }, action_hint="kick")
                data["fast_flags"] = 0
                data["timestamps"].clear()
        else:
            data["fast_flags"] = max(0, data["fast_flags"] - 1)

        # Slow timer detection (less common but still exploitable)
        if pps < self.MIN_PACKETS_PER_SEC and count > 5:  # need enough data
            data["slow_flags"] += 1
            if data["slow_flags"] >= self.FLAGS_REQUIRED:
                self.emit(player, 3, {
                    "type": "timer_slow",
                    "pps": f"{pps:.1f}",
                    "min": self.MIN_PACKETS_PER_SEC,
                })
                data["slow_flags"] = 0
                data["timestamps"].clear()
        else:
            data["slow_flags"] = max(0, data["slow_flags"] - 1)
