# chat_protection.py - Chat protection for Paradox AntiCheat
# Spam, advertising, profanity filtering, caps limiting, and mute system.

import re
import time
from collections import defaultdict, deque
from typing import Dict, Set
from endstone_paradox.modules.base import BaseModule


class ChatProtectionModule(BaseModule):
    """Chat protection suite.

    Features:
      - Spam detection (repeated messages, message flood)
      - Advertising filter (IPs, URLs, domains)
      - Swear/profanity filter (configurable word list)
      - Caps limiter (messages with >70% uppercase)
      - Command spam throttle
      - Mute system with duration
    """

    name = "chatprotection"

    # --- Advertising regex ---
    IP_PATTERN = re.compile(
        r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(:\d{1,5})?\b"
    )
    URL_PATTERN = re.compile(
        r"(https?://|www\.)\S+",
        re.IGNORECASE,
    )
    DOMAIN_PATTERN = re.compile(
        r"\b\S+\.(com|net|org|io|gg|me|xyz|co|us|uk|de|fr|ru|cn|tk|ml|ga|cf)\b",
        re.IGNORECASE,
    )

    # Domains that should never trigger the ad filter
    WHITELISTED_DOMAINS = {
        "minecraft.net", "mojang.com", "xbox.com",
    }

    # Default profanity words (kept short — server owners add their own)
    DEFAULT_SWEAR_LIST = [
        "fuck", "shit", "bitch", "ass", "dick", "cunt",
        "nigger", "nigga", "faggot", "retard",
    ]

    def on_start(self):
        self._anti_spam = self.db.get("config", "chat_anti_spam", True)
        self._anti_ads = self.db.get("config", "chat_anti_ads", True)
        self._anti_swear = self.db.get("config", "chat_anti_swear", True)
        self._caps_limit = self.db.get("config", "chat_caps_limit", True)
        self._caps_threshold = self.db.get("config", "chat_caps_threshold", 70)
        self._cmd_throttle = self.db.get("config", "chat_cmd_throttle", True)
        self._max_cmds_per_sec = self.db.get("config", "chat_max_cmds_per_sec", 3)

        # Spam thresholds
        self._spam_window = 5.0        # seconds
        self._spam_max_msgs = 4        # max messages in window
        self._repeat_threshold = 3     # same message N times in a row

        # Per-player tracking
        self._msg_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=20))
        self._cmd_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=20))
        self._last_msg: Dict[str, str] = {}
        self._repeat_count: Dict[str, int] = defaultdict(int)

        # Mute system: uuid -> expire_time (0=permanent)
        self._muted: Dict[str, float] = {}
        self._load_mutes()

        # Swear list
        stored_words = self.db.get("config", "swear_list")
        if stored_words and isinstance(stored_words, list):
            self._swear_words = set(w.lower() for w in stored_words)
        else:
            self._swear_words = set(self.DEFAULT_SWEAR_LIST)
            self.db.set("config", "swear_list", list(self._swear_words))

        # Whitelisted ad domains
        stored_wl = self.db.get("config", "ad_whitelist")
        if stored_wl and isinstance(stored_wl, list):
            self._ad_whitelist = set(d.lower() for d in stored_wl)
        else:
            self._ad_whitelist = set(self.WHITELISTED_DOMAINS)

    @property
    def check_interval(self) -> int:
        return 0  # event-driven only

    def check(self):
        pass

    # --- Main entry point (called from paradox.py on_player_chat) ---

    def on_player_chat(self, event) -> bool:
        """Process a chat message. Returns True if message should be blocked."""
        player = event.player
        message = event.message
        uuid_str = str(player.unique_id)

        # Admin bypass
        if self.plugin.security.is_level4(player):
            return False

        # Mute check
        if self._is_muted(uuid_str):
            player.send_message("§c[Paradox] You are muted.")
            return True

        now = time.time()

        # Command throttle
        if message.startswith("/"):
            if self._cmd_throttle:
                self._cmd_history[uuid_str].append(now)
                recent = sum(1 for t in self._cmd_history[uuid_str]
                             if now - t < 1.0)
                if recent > self._max_cmds_per_sec:
                    player.send_message("§c[Paradox] Command throttle — slow down.")
                    return True
            return False  # don't filter commands for swears/spam

        # Spam detection
        if self._anti_spam:
            self._msg_history[uuid_str].append(now)
            recent = sum(1 for t in self._msg_history[uuid_str]
                         if now - t < self._spam_window)
            if recent > self._spam_max_msgs:
                player.send_message("§c[Paradox] Slow down — too many messages.")
                self._emit_violation(player, "spam",
                                    {"rate": recent, "window": self._spam_window})
                return True

            # Repeat detection
            lower = message.strip().lower()
            if self._last_msg.get(uuid_str) == lower:
                self._repeat_count[uuid_str] += 1
                if self._repeat_count[uuid_str] >= self._repeat_threshold:
                    player.send_message("§c[Paradox] Stop repeating messages.")
                    self._emit_violation(player, "spam_repeat",
                                        {"repeats": self._repeat_count[uuid_str]})
                    return True
            else:
                self._repeat_count[uuid_str] = 0
            self._last_msg[uuid_str] = lower

        # Advertising filter
        if self._anti_ads and self._check_ads(message):
            player.send_message("§c[Paradox] Advertising is not allowed.")
            self._emit_violation(player, "advertising", {"message": message[:50]})
            return True

        # Swear filter
        if self._anti_swear and self._check_swears(message):
            player.send_message("§c[Paradox] Watch your language.")
            self._emit_violation(player, "profanity", {"message": message[:50]})
            return True

        # Caps limiter
        if self._caps_limit and len(message) > 5:
            alpha = [c for c in message if c.isalpha()]
            if alpha and len(alpha) > 5:
                upper_pct = sum(1 for c in alpha if c.isupper()) / len(alpha) * 100
                if upper_pct >= self._caps_threshold:
                    player.send_message("§c[Paradox] Too many capital letters.")
                    return True

        return False

    # --- Mute system ---

    def mute_player(self, uuid_str: str, duration: float = 0):
        """Mute a player. duration=0 means permanent."""
        expire = time.time() + duration if duration > 0 else 0
        self._muted[uuid_str] = expire
        self._save_mutes()

    def unmute_player(self, uuid_str: str):
        self._muted.pop(uuid_str, None)
        self._save_mutes()

    def is_muted(self, uuid_str: str) -> bool:
        return self._is_muted(uuid_str)

    def _is_muted(self, uuid_str: str) -> bool:
        if uuid_str not in self._muted:
            return False
        expire = self._muted[uuid_str]
        if expire == 0:
            return True  # permanent
        if time.time() < expire:
            return True
        # Expired
        self._muted.pop(uuid_str, None)
        self._save_mutes()
        return False

    def _load_mutes(self):
        data = self.db.get("config", "muted_players")
        if data and isinstance(data, dict):
            self._muted = {k: float(v) for k, v in data.items()}

    def _save_mutes(self):
        self.db.set("config", "muted_players", self._muted)

    # --- Swear word management ---

    def add_swear_word(self, word: str):
        self._swear_words.add(word.lower())
        self.db.set("config", "swear_list", list(self._swear_words))

    def remove_swear_word(self, word: str):
        self._swear_words.discard(word.lower())
        self.db.set("config", "swear_list", list(self._swear_words))

    # --- Internal detection helpers ---

    def _check_ads(self, message: str) -> bool:
        lower = message.lower()

        if self.IP_PATTERN.search(message):
            return True

        if self.URL_PATTERN.search(message):
            return True

        match = self.DOMAIN_PATTERN.search(lower)
        if match:
            domain = match.group(0)
            if domain not in self._ad_whitelist:
                return True

        return False

    def _check_swears(self, message: str) -> bool:
        lower = message.lower()
        # Strip common leet-speak substitutions
        cleaned = lower.replace("@", "a").replace("0", "o").replace("1", "i") \
                       .replace("3", "e").replace("$", "s").replace("!", "i")

        words = re.split(r"[\s.,!?;:\-_]+", cleaned)
        for word in words:
            if word in self._swear_words:
                return True
        return False

    def _emit_violation(self, player, sub_type: str, evidence: dict):
        evidence["sub_type"] = sub_type
        if hasattr(self.plugin, 'violation_engine'):
            self.plugin.violation_engine.emit_violation(
                player, "chatprotection", 2, evidence, "cancel"
            )

    def on_player_leave(self, player):
        uuid_str = str(player.unique_id)
        self._msg_history.pop(uuid_str, None)
        self._cmd_history.pop(uuid_str, None)
        self._last_msg.pop(uuid_str, None)
        self._repeat_count.pop(uuid_str, None)
