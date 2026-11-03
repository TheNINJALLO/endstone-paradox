import json
from pathlib import Path

from endstone.event import PacketReceiveEvent, PacketSendEvent, event_handler
from endstone.plugin import Plugin


class Probe(Plugin):
    api_version = '0.11'
    version = '1.0.0'

    def on_enable(self):
        self.payloads = []
        self.register_events(self)

    def capture(self, event, outgoing):
        if len(self.payloads) >= 120:
            return
        if outgoing and event.packet_id not in (19, 28, 40):
            return
        if not outgoing and event.packet_id not in (48, 144, 175):
            return
        self.payloads.append({'id': event.packet_id, 'outgoing': outgoing, 'payload': bytes(event.payload).hex()})
        Path('native-payloads.json').write_text(json.dumps(self.payloads))

    @event_handler
    def receive(self, event: PacketReceiveEvent):
        self.capture(event, False)

    @event_handler
    def send(self, event: PacketSendEvent):
        self.capture(event, True)
