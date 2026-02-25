"""
Paradox AntiCheat - Rate Limit Module

Monitors incoming packets and enforces rate limits.
Detects DoS attacks and can trigger server lockdown.
"""

import time
from collections import deque
from endstone_paradox.modules.base import BaseModule


class RateLimitModule(BaseModule):
    """Packet rate limiting and DoS detection."""

    name = "ratelimit"

    MAX_PACKETS_PER_WINDOW = 2000  # Max packets in the time window (Bedrock sends 500+ normally)
    WINDOW_SIZE = 1.0              # 1 second
    VIOLATION_THRESHOLD = 20       # Violations before kick (very generous)
    DOS_PLAYER_THRESHOLD = 5      # Players violating simultaneously = DoS
    DOS_TIME_WINDOW = 10.0        # Window for DoS detection
    LOCKDOWN_DURATION = 60        # Lockdown duration in seconds

    def on_start(self):
        self._packet_counts = {}   # UUID -> deque of timestamps
        self._violations = {}      # UUID -> count
        self._dos_violations = deque()  # timestamps of rate limit violations

    def on_stop(self):
        self._packet_counts.clear()
        self._violations.clear()
        self._dos_violations.clear()

    def on_player_leave(self, player):
        uuid_str = str(player.unique_id)
        self._packet_counts.pop(uuid_str, None)
        self._violations.pop(uuid_str, None)

    def on_packet(self, event):
        """Monitor incoming packet rates."""
        player = event.player
        if player is None:
            return
        if self.plugin.security.is_level4(player):
            return

        uuid_str = str(player.unique_id)
        now = time.time()

        # Track packet timestamps
        packets = self._packet_counts.setdefault(uuid_str, deque())
        packets.append(now)

        # Remove old packets
        while packets and (now - packets[0]) > self.WINDOW_SIZE:
            packets.popleft()

        if len(packets) > self.MAX_PACKETS_PER_WINDOW:
            # Rate limit violation
            violations = self._violations.get(uuid_str, 0) + 1
            self._violations[uuid_str] = violations

            # Track for DoS detection
            self._dos_violations.append(now)
            while self._dos_violations and (now - self._dos_violations[0]) > self.DOS_TIME_WINDOW:
                self._dos_violations.popleft()

            # Cancel the packet
            event.is_cancelled = True

            if violations >= self.VIOLATION_THRESHOLD:
                # Kick the player (not ban — avoids false positives)
                player.kick("§cKicked: Excessive packet rate detected.")
                self.alert_admins(
                    f"§c{player.name}§e kicked for packet flooding "
                    f"({violations} violations)"
                )
                self._violations.pop(uuid_str, None)
                self._packet_counts.pop(uuid_str, None)
            else:
                self.alert_admins(
                    f"§c{player.name}§e rate limited "
                    f"({len(packets)} packets/s, violation #{violations})"
                )

            # DoS detection
            if len(self._dos_violations) >= self.DOS_PLAYER_THRESHOLD:
                self._trigger_lockdown()

    def _trigger_lockdown(self):
        """Trigger server lockdown due to detected DoS attack."""
        if self.plugin._lockdown_active:
            return

        self.plugin._lockdown_active = True
        self.plugin.db.set("config", "lockdown", True)

        self.alert_admins(
            f"§4§l[DOS DETECTED]§r§e Server entering lockdown for "
            f"{self.LOCKDOWN_DURATION}s!"
        )

        # Kick all non-Level4 players
        for player in self.plugin.server.online_players:
            if not self.plugin.security.is_level4(player):
                player.kick("§cServer lockdown: DoS attack detected.")

        # Schedule lockdown release
        def release_lockdown():
            self.plugin._lockdown_active = False
            self.plugin.db.set("config", "lockdown", False)
            self.alert_admins("§2[§7Paradox§2]§a Lockdown released.")

        ticks = self.LOCKDOWN_DURATION * 20
        self.plugin.server.scheduler.run_task(
            self.plugin, release_lockdown, delay=ticks
        )
