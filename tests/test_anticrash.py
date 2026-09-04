from types import SimpleNamespace

from bedrock_protocol.packets import MinecraftPacketIds

from endstone_paradox.modules.anticrash import (
    SUBCHUNK_REQUEST_PACKET_ID,
    AntiCrashModule,
)


class FakePlayer:
    name = "CrashTester"

    def __init__(self):
        self.kick_reason = None

    def kick(self, reason):
        self.kick_reason = reason


class FakeViolationEngine:
    def __init__(self):
        self.events = []

    def emit_violation(self, player, module, severity, evidence, action_hint):
        self.events.append((player, module, severity, evidence, action_hint))


class FakePlugin:
    def __init__(self):
        self.db = SimpleNamespace()
        self.logger = SimpleNamespace()
        self.violation_engine = FakeViolationEngine()
        self.admin_messages = []

    def send_to_level4(self, message):
        self.admin_messages.append(message)


def make_event(payload_size):
    return SimpleNamespace(
        packet_id=SUBCHUNK_REQUEST_PACKET_ID,
        payload=b"x" * payload_size,
        is_cancelled=False,
        player=FakePlayer(),
    )


def test_uses_protocol_subchunk_request_packet_id():
    assert SUBCHUNK_REQUEST_PACKET_ID == MinecraftPacketIds.SubChunkRequestPacket


def test_allows_subchunk_request_at_size_limit():
    module = AntiCrashModule(FakePlugin())
    module.running = True
    event = make_event(module.MAX_PACKET_SIZE)

    module.on_packet(event)

    assert event.is_cancelled is False
    assert event.player.kick_reason is None


def test_blocks_oversized_subchunk_request():
    plugin = FakePlugin()
    module = AntiCrashModule(plugin)
    module.running = True
    event = make_event(module.MAX_PACKET_SIZE + 1)

    module.on_packet(event)

    assert event.is_cancelled is True
    assert "Crasher exploit detected" in event.player.kick_reason
    assert plugin.admin_messages
    assert plugin.violation_engine.events[0][1:3] == ("anticrash", 5)
    assert plugin.violation_engine.events[0][4] == "ban"
