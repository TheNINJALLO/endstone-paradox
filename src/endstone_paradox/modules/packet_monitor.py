"""
Paradox AntiCheat - Packet Monitor Module

Monitors packet types and frequency for diagnostic purposes.
Warns in console when packet spam is detected.
"""

import time
from collections import defaultdict, deque
from endstone_paradox.modules.base import BaseModule


class PacketMonitorModule(BaseModule):
    """Packet frequency monitoring and spam detection."""

    name = "packetmonitor"
    check_interval = 100  # Cleanup every 5 seconds

    SPAM_THRESHOLD = 250   # Packets per type per 5 seconds
    WINDOW_SIZE = 5.0      # Analysis window

    # Common/noisy packet types to ignore
    IGNORED_PACKETS = {
        "MovePlayerPacket",
        "PlayerAuthInputPacket",
        "LevelChunkPacket",
        "NetworkChunkPublisherUpdatePacket",
    }

    def on_start(self):
        self._packet_data = {}  # UUID -> {packet_type: deque of timestamps}

    def on_stop(self):
        self._packet_data.clear()

    def on_player_leave(self, player):
        self._packet_data.pop(str(player.unique_id), None)

    def on_packet(self, event):
        """Track packet types and frequency."""
        player = event.player
        if player is None:
            return

        uuid_str = str(player.unique_id)
        now = time.time()

        # Get packet type name
        packet_type = getattr(event, 'packet_type', 'Unknown')
        if isinstance(packet_type, int):
            packet_type = f"PacketID_{packet_type}"
        else:
            packet_type = str(packet_type)

        # Skip ignored types
        if packet_type in self.IGNORED_PACKETS:
            return

        player_data = self._packet_data.setdefault(uuid_str, defaultdict(deque))
        timestamps = player_data[packet_type]
        timestamps.append(now)

        # Clean old entries
        while timestamps and (now - timestamps[0]) > self.WINDOW_SIZE:
            timestamps.popleft()

        # Check for spam
        if len(timestamps) >= self.SPAM_THRESHOLD:
            self.logger.warning(
                f"[Paradox] Packet spam: {player.name} sent "
                f"{len(timestamps)}x {packet_type} in {self.WINDOW_SIZE}s"
            )
            timestamps.clear()

    def check(self):
        """Periodic cleanup of old packet data."""
        now = time.time()
        to_remove = []
        for uuid_str, data in self._packet_data.items():
            empty_types = []
            for ptype, timestamps in data.items():
                while timestamps and (now - timestamps[0]) > self.WINDOW_SIZE:
                    timestamps.popleft()
                if not timestamps:
                    empty_types.append(ptype)
            for ptype in empty_types:
                del data[ptype]
            if not data:
                to_remove.append(uuid_str)
        for uuid_str in to_remove:
            del self._packet_data[uuid_str]
