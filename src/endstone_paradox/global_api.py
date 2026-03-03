# global_api.py - Client for the Paradox Global Ban API
# Auto-registers on first connect, syncs bans/flags, pushes violations.

import base64
import json
import socket
import time
import urllib.request
import urllib.error
from threading import Thread, Lock
from typing import Optional

# ── Obfuscated official endpoint ─────────────────────────
# XOR + base64 encoded to prevent casual source-code discovery
_EK = b"ParadoxAC"
_EP = "OBUGEV5AV3V2flBGUkpeQXdtYVdCW1xfQXE="


def _resolve_endpoint() -> str:
    """Decode the official API endpoint at runtime."""
    try:
        raw = base64.b64decode(_EP)
        return bytes([b ^ _EK[i % len(_EK)] for i, b in enumerate(raw)]).decode()
    except Exception:
        return ""


class GlobalAPIClient:
    """HTTP client for the Paradox Global Ban API.

    Flow:
    1. Server owner sets global_database.enabled = true and global_database.api_url
    2. On plugin enable, client auto-registers via /api/servers/self-register
    3. API key is stored back to config.toml for future use
    4. Periodic sync pulls new bans/flags
    5. Violation reports are pushed in batches
    """

    def __init__(self, plugin):
        self.plugin = plugin
        self.logger = plugin.logger
        self.config = plugin.paradox_config
        self.db = plugin.db

        self._api_url = ""
        self._api_key = ""
        self._server_name = ""
        self._sync_interval = 300
        self._last_sync = 0.0
        self._running = False
        self._report_buffer = []
        self._sync_task = None
        self._register_lock = Lock()
        self._registered = False

    # ── Lifecycle ────────────────────────────────────────────

    def start(self):
        """Initialize and start the global API client."""
        self._api_url = (self.config.get("global_database", "api_url", default="") or "").rstrip("/")
        if not self._api_url:
            self._api_url = _resolve_endpoint()  # Official endpoint (obfuscated)
        self._api_key = self.config.get("global_database", "api_key", default="") or ""
        self._server_name = self.config.get("global_database", "server_name", default="") or ""
        self._sync_interval = self.config.get("global_database", "sync_interval", default=300) or 300

        if not self._api_url:
            self.logger.warning("§2[§7Paradox§2]§e Global DB: no api_url configured, skipping.")
            return

        # Default server name to hostname
        if not self._server_name:
            self._server_name = socket.gethostname()

        self._running = True

        # Auto-register if no API key (runs in background, retries on sync)
        if not self._api_key:
            self.logger.info("§2[§7Paradox§2]§a Global DB: No API key — will auto-register...")

        # Always start the sync loop — it will attempt registration if needed
        self._start_sync_loop()

    def stop(self):
        """Stop the sync loop and flush remaining reports."""
        self._running = False
        self._sync_task = None
        # Flush any remaining reports
        if self._report_buffer:
            Thread(target=self._flush_reports, daemon=True).start()

    # ── Auto-Registration ────────────────────────────────────

    def _auto_register(self):
        """Register this server with the Global Ban API (thread-safe)."""
        # Prevent concurrent registration attempts
        if not self._register_lock.acquire(blocking=False):
            return False  # Another thread is already registering
        try:
            # Double-check after acquiring lock
            if self._api_key or self._registered:
                return True

            body = json.dumps({"name": self._server_name}).encode("utf-8")
            req = urllib.request.Request(
                f"{self._api_url}/api/servers/self-register",
                data=body,
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            resp = urllib.request.urlopen(req, timeout=15)
            data = json.loads(resp.read().decode("utf-8"))

            api_key = data.get("api_key", "")
            server_id = data.get("server_id", "")

            if api_key:
                self._api_key = api_key
                self._registered = True
                # Persist the key to config.toml
                self.config.set("global_database", "api_key", api_key)
                self.logger.info(
                    f"§2[§7Paradox§2]§a Global DB: Registered as '{self._server_name}' "
                    f"(id: {server_id[:8]}...)"
                )
                return True
            else:
                self.logger.error("§2[§7Paradox§2]§c Global DB: Registration returned no API key")
                return False

        except urllib.error.HTTPError as e:
            error_body = ""
            try:
                error_body = e.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            self.logger.error(
                f"§2[§7Paradox§2]§c Global DB: Registration failed (HTTP {e.code}): {error_body}"
            )
            return False
        except (urllib.error.URLError, ConnectionError, OSError):
            # API not reachable yet — silent, will retry on next sync
            return False
        except Exception as e:
            self.logger.warning(f"§2[§7Paradox§2]§e Global DB: Registration pending: {e}")
            return False
        finally:
            self._register_lock.release()

    # ── Sync Loop ────────────────────────────────────────────

    def _start_sync_loop(self):
        """Start the periodic sync loop via scheduler."""
        if not self._running:
            return
        self._do_sync_tick()

    def _do_sync_tick(self):
        """Single sync tick — pull updates, flush reports, reschedule."""
        if not self._running:
            return

        # Run sync in background thread to avoid blocking
        Thread(target=self._sync_now, daemon=True).start()

        # Reschedule (sync_interval seconds = interval * 20 ticks)
        interval_ticks = max(200, self._sync_interval * 20)
        try:
            self._sync_task = self.plugin.server.scheduler.run_task(
                self.plugin, self._do_sync_tick, delay=interval_ticks
            )
        except Exception:
            pass

    def _sync_now(self):
        """Pull ban/flag updates from the API and apply them locally."""
        # If no API key yet, try to register first
        if not self._api_key:
            self._auto_register()
            if not self._api_key:
                return  # Still no key — API probably not reachable yet

        try:
            since = self._last_sync
            req = urllib.request.Request(
                f"{self._api_url}/api/sync?since={since}",
                headers={"X-API-Key": self._api_key},
            )
            resp = urllib.request.urlopen(req, timeout=15)
            data = json.loads(resp.read().decode("utf-8"))

            bans = data.get("bans", [])
            server_time = data.get("server_time", time.time())

            applied = 0
            for ban in bans:
                player_name = ban.get("player_name", "")
                category = ban.get("category", "ban")
                reason = ban.get("reason", "Global ban")

                if not player_name:
                    continue

                # Store in local DB based on category
                if category == "ban":
                    key = player_name.lower()
                    if not self.db.has("global_bans", key):
                        self.db.set("global_bans", key, {
                            "name": player_name,
                            "reason": reason,
                            "category": category,
                            "source": ban.get("source_server", "global"),
                            "synced_at": time.time(),
                        })
                        applied += 1
                elif category in ("high_risk", "flagged"):
                    key = player_name.lower()
                    if not self.db.has("global_flags", key):
                        self.db.set("global_flags", key, {
                            "name": player_name,
                            "reason": reason,
                            "category": category,
                            "source": ban.get("source_server", "global"),
                            "synced_at": time.time(),
                        })
                        applied += 1

            self._last_sync = server_time

            if applied > 0:
                self.logger.info(
                    f"§2[§7Paradox§2]§a Global DB: Synced {applied} new entries"
                )

            # Flush any buffered reports
            self._flush_reports()

        except urllib.error.HTTPError as e:
            if e.code == 401:
                self.logger.warning(
                    "§2[§7Paradox§2]§e Global DB: API key rejected — "
                    "you may need to re-register"
                )
            else:
                self.logger.warning(
                    f"§2[§7Paradox§2]§e Global DB: Sync failed (HTTP {e.code})"
                )
        except (urllib.error.URLError, ConnectionError, OSError):
            # API not reachable — silent, will retry next sync
            pass
        except Exception as e:
            self.logger.warning(f"§2[§7Paradox§2]§e Global DB: Sync failed: {e}")

    # ── Player Checking ──────────────────────────────────────

    def is_globally_banned(self, player_name: str) -> bool:
        """Check if a player is on the global ban list (local cache)."""
        return self.db.has("global_bans", player_name.lower())

    def is_high_risk(self, player_name: str) -> Optional[dict]:
        """Check if a player is flagged/high-risk (local cache)."""
        return self.db.get("global_flags", player_name.lower())

    def check_player_on_join(self, player) -> bool:
        """Check a player against the global database on join.

        Returns True if the player is allowed, False if they should be kicked.
        """
        name = player.name

        # Check global bans
        ban = self.db.get("global_bans", name.lower())
        if ban:
            reason = ban.get("reason", "Globally banned")
            player.kick(f"§c[Paradox Global] {reason}")
            self.logger.info(
                f"§2[§7Paradox§2]§c Kicked globally banned player: {name}"
            )
            return False

        # Check high-risk flags (don't kick, just alert staff)
        flag = self.db.get("global_flags", name.lower())
        if flag:
            category = flag.get("category", "flagged")
            reason = flag.get("reason", "")
            self.plugin.send_to_level4(
                f"§2[§7Paradox§2]§e ⚠ {name} is globally {category}: {reason}"
            )

        return True

    # ── Report Pushing ───────────────────────────────────────

    def push_report(self, player_name: str, module: str, severity: int = 3,
                    evidence: dict = None, player_xuid: str = ""):
        """Buffer a violation report for batch pushing."""
        self._report_buffer.append({
            "player_name": player_name,
            "player_xuid": player_xuid,
            "module": module,
            "severity": severity,
            "evidence": evidence or {},
        })

        # Auto-flush if buffer gets large
        if len(self._report_buffer) >= 20:
            Thread(target=self._flush_reports, daemon=True).start()

    def _flush_reports(self):
        """Push buffered reports to the API."""
        if not self._report_buffer or not self._api_key or not self._api_url:
            return

        # Grab current buffer and reset
        batch = self._report_buffer[:]
        self._report_buffer.clear()

        try:
            body = json.dumps({"reports": batch}).encode("utf-8")
            req = urllib.request.Request(
                f"{self._api_url}/api/report/batch",
                data=body,
                method="POST",
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": self._api_key,
                },
            )
            urllib.request.urlopen(req, timeout=15)
        except Exception:
            # Put reports back on failure (best-effort)
            self._report_buffer.extend(batch)

    # ── Ban Pushing ──────────────────────────────────────────

    def push_ban(self, player_name: str, reason: str = "",
                 player_xuid: str = "", category: str = "ban"):
        """Push a local ban to the global database."""
        if not self._api_key or not self._api_url:
            return

        def _push():
            try:
                body = json.dumps({
                    "player_name": player_name,
                    "player_xuid": player_xuid,
                    "reason": reason,
                    "category": category,
                }).encode("utf-8")
                req = urllib.request.Request(
                    f"{self._api_url}/api/bans",
                    data=body,
                    method="POST",
                    headers={
                        "Content-Type": "application/json",
                        "X-API-Key": self._api_key,
                    },
                )
                urllib.request.urlopen(req, timeout=15)
            except Exception:
                pass

        Thread(target=_push, daemon=True).start()

    # ── Helpers ──────────────────────────────────────────────

    def _schedule_on_server(self, fn):
        """Schedule a function to run on the server's main thread."""
        try:
            self.plugin.server.scheduler.run_task(self.plugin, fn, delay=1)
        except Exception:
            fn()
