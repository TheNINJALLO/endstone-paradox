# lag_clear.py - Periodic ground item cleanup
# Excludes name-tagged entities and NPCs (custom or vanilla).

import time
from endstone_paradox.modules.base import BaseModule


class LagClearModule(BaseModule):
    """Scheduled entity cleanup for lag reduction.

    Clears ground items, stale arrows, and XP orbs on a timer.
    Protects:
      - Name-tagged entities (pets, custom mobs)
      - NPCs (vanilla type=npc or entities with NPC component)
      - Players
    """

    name = "lagclear"

    DEFAULT_INTERVAL = 300  # 5 minutes in seconds

    # Entity types to clear (each gets its own selector for safety)
    # 'name=' (empty) filters to ONLY unnamed entities; named ones are kept.
    CLEAR_TARGETS = [
        "item",       # Ground items (drops)
        "arrow",      # Stale arrows
        "xp_orb",     # XP orbs
    ]

    def on_start(self):
        self._interval = self.db.get("config", "lagclear_interval", self.DEFAULT_INTERVAL)
        if isinstance(self._interval, str):
            self._interval = int(self._interval)
        self._last_clear = time.time()
        self._warning_sent = False

    @property
    def check_interval(self) -> int:
        return 200  # Check every 10 seconds

    def check(self):
        """Check if it's time for a lag clear."""
        now = time.time()
        elapsed = now - self._last_clear

        # Send warning 30 seconds before clear
        if elapsed >= self._interval - 30 and not self._warning_sent:
            self._warning_sent = True
            for player in self.plugin.server.online_players:
                player.send_message(
                    "§2[§7Paradox§2]§e Ground items will be cleared in 30 seconds!"
                )

        if elapsed >= self._interval:
            self._perform_clear()
            self._last_clear = now
            self._warning_sent = False

    def _perform_clear(self):
        """Remove ground items, arrows, and XP orbs from all dimensions.

        Uses entity selectors that:
          - Only target specific, harmless entity types
          - Skip name-tagged entities (name= empty selector)
          - Never target NPCs or players
        """
        server = self.plugin.server
        sender = server.command_sender
        cleared_any = False

        for etype in self.CLEAR_TARGETS:
            try:
                # Selector: only unnamed entities of this type
                # type=<type> — limits to this entity type
                # name= — empty name selector = only unnamed entities (protects name tags)
                # This command silently succeeds even with 0 matches on most Bedrock servers.
                # We wrap in try/except to suppress any "No targets" error.
                if etype == "xp_orb":
                    # XP orbs never have names, no need for name filter
                    cmd = f"kill @e[type={etype}]"
                else:
                    cmd = f"kill @e[type={etype},name=]"

                server.dispatch_command(sender, cmd)
                cleared_any = True
            except Exception:
                # "No targets matched selector" or similar — silently ignore
                pass

        if cleared_any:
            for player in server.online_players:
                player.send_message(
                    "§2[§7Paradox§2]§a Ground items have been cleared!"
                )

    def set_interval(self, seconds: int):
        """Update the lag clear interval."""
        self._interval = max(60, seconds)  # Minimum 1 minute
        self.db.set("config", "lagclear_interval", self._interval)

    def force_clear(self):
        """Force an immediate lag clear."""
        self._perform_clear()
        self._last_clear = time.time()
        self._warning_sent = False
