import time
from endstone.event import PacketReceiveEvent
from bedrock_protocol.packets import MinecraftPacketIds
from endstone_paradox.modules.base import BaseModule

class AntiCrashModule(BaseModule):
    """Blocks oversized SubChunkRequestPacket exploits."""

    name = "anticrash"
    MAX_PACKET_SIZE = 16384  # 16KB

    def on_packet(self, event: PacketReceiveEvent):
        if not self.running:
            return

        # Use bedrock-protocol-packets MinecraftPacketIds to identify SubChunkRequest
        if event.packet_id == MinecraftPacketIds.SubChunkRequest:
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
