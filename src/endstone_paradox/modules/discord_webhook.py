# discord_webhook.py - Discord webhook integration for Paradox AntiCheat
# Sends violation alerts, ban notifications, and evidence to Discord via webhooks.

import time
import json
import threading
import urllib.request
import ssl
from collections import deque
from typing import Optional
from endstone_paradox.modules.base import BaseModule


class DiscordWebhookModule(BaseModule):
    """Discord webhook integration.

    Hooks into the violation engine to forward alerts to Discord channels.
    Supports:
      - Violation alerts (colour-coded by severity)
      - Ban / kick notifications
      - Configurable severity filter (minimum severity to send)
      - Rate limiting to avoid Discord API throttling
      - Non-blocking sends via background thread
    """

    name = "discord"

    # Severity colours (Discord embed colour as int)
    COLOURS = {
        1: 0x95A5A6,   # INFO – grey
        2: 0x3498DB,   # LOW – blue
        3: 0xF1C40F,   # MEDIUM – yellow
        4: 0xE67E22,   # HIGH – orange
        5: 0xE74C3C,   # CRITICAL – red
    }

    SEVERITY_NAMES = {1: "Info", 2: "Low", 3: "Medium", 4: "High", 5: "Critical"}

    def on_start(self):
        self._webhook_url = self.db.get("config", "discord_webhook_url", "")
        self._min_severity = self.db.get("config", "discord_min_severity", 3)
        self._send_bans = self.db.get("config", "discord_send_bans", True)
        self._send_kicks = self.db.get("config", "discord_send_kicks", True)
        self._footer_text = self.db.get("config", "discord_footer_text", "Paradox AntiCheat")

        # Also check config.toml values
        try:
            pc = getattr(self.plugin, 'paradox_config', None) or getattr(self.plugin, '_paradox_config', None)
            if pc:
                if not self._webhook_url:
                    self._webhook_url = pc.get("discord", "webhook_url", default="") or ""
                self._min_severity = pc.get("discord", "min_severity", default=3) or 3
                send_bans = pc.get("discord", "send_bans", default=True)
                if send_bans is not None:
                    self._send_bans = send_bans
                send_kicks = pc.get("discord", "send_kicks", default=True)
                if send_kicks is not None:
                    self._send_kicks = send_kicks
        except Exception as e:
            self.logger.warning(f"§2[§7Paradox§2]§e Discord config load error: {e}")

        if self._webhook_url:
            self.logger.info(f"§2[§7Paradox§2]§a Discord webhook configured")
        else:
            self.logger.warning(f"§2[§7Paradox§2]§e Discord module enabled but no webhook URL set")

        # Rate limiting: max 5 messages per 5 seconds
        self._send_times = deque(maxlen=5)
        self._queue = deque(maxlen=100)
        self._ctx = ssl.create_default_context()

        # Background sender thread
        self._running_flag = True
        self._thread = threading.Thread(target=self._sender_loop, daemon=True)
        self._thread.start()

    def on_stop(self):
        self._running_flag = False

    @property
    def check_interval(self) -> int:
        return 0  # no periodic check needed

    def check(self):
        pass  # event-driven only

    # --- Public API called by violation engine hook ---

    def on_violation(self, player_name: str, player_uuid: str,
                     module: str, severity: int, evidence: dict,
                     action: str):
        """Called when a violation is emitted."""
        if not self._webhook_url:
            return
        if severity < self._min_severity:
            return

        colour = self.COLOURS.get(severity, 0x95A5A6)
        sev_name = self.SEVERITY_NAMES.get(severity, "Unknown")

        fields = [
            {"name": "Player", "value": f"`{player_name}`", "inline": True},
            {"name": "Module", "value": f"`{module}`", "inline": True},
            {"name": "Severity", "value": f"**{sev_name}**", "inline": True},
            {"name": "Action", "value": f"`{action}`", "inline": True},
        ]

        # Add evidence fields (limit to 5 to avoid embed size issues)
        ev_items = list(evidence.items())[:5]
        if ev_items:
            ev_text = "\n".join(f"**{k}**: `{v}`" for k, v in ev_items)
            fields.append({"name": "Evidence", "value": ev_text, "inline": False})

        embed = {
            "title": f"⚠️ {module} Violation",
            "color": colour,
            "fields": fields,
            "footer": {"text": self._footer_text},
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

        self._enqueue({"embeds": [embed]})

    def on_ban(self, player_name: str, reason: str, banner: str = "AutoBan"):
        """Called when a player is banned."""
        if not self._webhook_url or not self._send_bans:
            return
        embed = {
            "title": "🔨 Player Banned",
            "color": 0xE74C3C,
            "fields": [
                {"name": "Player", "value": f"`{player_name}`", "inline": True},
                {"name": "Banned By", "value": f"`{banner}`", "inline": True},
                {"name": "Reason", "value": reason, "inline": False},
            ],
            "footer": {"text": self._footer_text},
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        self._enqueue({"embeds": [embed]})

    def on_kick(self, player_name: str, reason: str):
        """Called when a player is kicked."""
        if not self._webhook_url or not self._send_kicks:
            return
        embed = {
            "title": "👢 Player Kicked",
            "color": 0xE67E22,
            "fields": [
                {"name": "Player", "value": f"`{player_name}`", "inline": True},
                {"name": "Reason", "value": reason, "inline": False},
            ],
            "footer": {"text": self._footer_text},
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        self._enqueue({"embeds": [embed]})

    # --- Internal ---

    def _enqueue(self, payload: dict):
        self._queue.append(payload)

    def _sender_loop(self):
        """Background thread that drains the queue with rate limiting."""
        while self._running_flag:
            time.sleep(0.5)

            while self._queue and self._running_flag:
                # Hot-reload webhook URL from config (so changes apply without restart)
                try:
                    pc = getattr(self.plugin, 'paradox_config', None) or getattr(self.plugin, '_paradox_config', None)
                    if pc:
                        new_url = pc.get("discord", "webhook_url", default="") or ""
                        if new_url:
                            self._webhook_url = new_url
                except Exception:
                    pass

                if not self._webhook_url:
                    self._queue.clear()
                    break

                # Rate limit: max 5 per 5 seconds
                now = time.time()
                while self._send_times and (now - self._send_times[0]) > 5.0:
                    self._send_times.popleft()
                if len(self._send_times) >= 5:
                    time.sleep(1.0)
                    continue

                payload = self._queue.popleft()
                try:
                    data = json.dumps(payload).encode("utf-8")
                    req = urllib.request.Request(
                        self._webhook_url,
                        data=data,
                        method="POST",
                        headers={
                            "Content-Type": "application/json",
                            "User-Agent": "ParadoxAntiCheat/1.7 (Endstone Plugin)",
                        },
                    )
                    urllib.request.urlopen(req, context=self._ctx, timeout=10)
                    self._send_times.append(time.time())
                except Exception as e:
                    if hasattr(self, 'logger') and self.logger:
                        self.logger.warning(f"§2[§7Paradox§2]§e Discord webhook send failed: {e}")
