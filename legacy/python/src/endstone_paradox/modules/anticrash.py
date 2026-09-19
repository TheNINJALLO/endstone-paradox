from endstone.event import PacketReceiveEvent
from bedrock_protocol.packets import MinecraftPacketIds
from endstone_paradox.modules.base import BaseModule


SUBCHUNK_REQUEST_PACKET_ID = getattr(
    MinecraftPacketIds,
    "SubChunkRequestPacket",
    getattr(MinecraftPacketIds, "SubChunkRequest", 175),
)


class AntiCrashModule(BaseModule):
    """Blocks oversized SubChunkRequestPacket exploits."""

    name = "anticrash"
    MAX_PACKET_SIZE = 16384  # 16KB

    def on_packet(self, event: PacketReceiveEvent):
        if not self.running:
            return

        # The protocol package names packet 175 SubChunkRequestPacket. Retain
        # fallbacks above so older package builds do not break the handler.
        if event.packet_id == SUBCHUNK_REQUEST_PACKET_ID:
            payload_size = len(event.payload)
            if payload_size > self.MAX_PACKET_SIZE:
                event.is_cancelled = True
                
                player = event.player
                if player:
                    size_kb = payload_size / 1024
                    # Immediate kick
                    player.kick("§c[Paradox] Crasher exploit detected.")
                    
                    # Notify admins
                    self.plugin.send_to_level4(f"§2[§7Paradox§2]§o§7 §e[Anti-Crash]§7 Blocked crash attempt from §f{player.name} §e[{size_kb:.2f}KB]§7.")
                    
                    # Log ban manually to banlist if we want (or emit violation)
                    self.emit(player, 5, {
                        "type": "crash_exploit",
                        "desc": f"Oversized SubChunkRequestPacket ({size_kb:.2f}KB)",
                    }, action_hint="ban")
