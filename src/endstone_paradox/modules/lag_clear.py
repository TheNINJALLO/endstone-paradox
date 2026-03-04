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

        Uses the Endstone dimension API to iterate entities directly,
        avoiding command selector syntax issues.  Skips any entity that
        has a custom name (name-tagged pets, custom mobs).
        """
        total_cleared = 0

        for player in self.plugin.server.online_players:
            try:
                dim = player.dimension
                for entity in dim.get_entities():
                    try:
                        etype = str(entity.type).lower().replace("minecraft:", "")

                        # Only clear our target types
                        if etype not in ("item", "arrow", "xp_orb"):
                            continue

                        # Skip named entities (name-tagged pets, etc.)
                        if etype != "xp_orb":  # XP orbs never have names
                            ent_name = getattr(entity, 'name_tag', None) or getattr(entity, 'custom_name', None)
                            if ent_name and str(ent_name).strip():
                                continue

                        entity.kill()
                        total_cleared += 1
                    except Exception:
                        pass
            except Exception:
                pass

        if total_cleared > 0:
            for player in self.plugin.server.online_players:
                player.send_message(
                    f"§2[§7Paradox§2]§a Cleared {total_cleared} ground items/arrows/XP orbs!"
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
