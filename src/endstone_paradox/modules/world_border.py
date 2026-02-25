# world_border.py - Configurable world border enforcement

import math
from endstone_paradox.modules.base import BaseModule


class WorldBorderModule(BaseModule):
    """Enforces a configurable world border."""

    name = "worldborder"
    check_interval = 40  # Check every 2 seconds

    def on_start(self):
        # Load config
        config = self.db.get("config", "worldborder", {})
        self._radius = config.get("radius", 10000)
        self._center_x = config.get("center_x", 0)
        self._center_z = config.get("center_z", 0)
        self._enabled = config.get("enabled", True)

    def check(self):
        """Check all players are within the world border."""
        if not self._enabled:
            return

        for player in self.plugin.server.online_players:
            try:
                if self.plugin.security.is_level4(player):
                    continue

                loc = player.location
                dx = loc.x - self._center_x
                dz = loc.z - self._center_z
                distance = math.sqrt(dx * dx + dz * dz)

                if distance > self._radius:
                    # Calculate teleport position (just inside border)
                    ratio = (self._radius - 5) / distance
                    safe_x = self._center_x + dx * ratio
                    safe_z = self._center_z + dz * ratio

                    player.teleport(
                        player.dimension.get_block(
                            int(safe_x), int(loc.y), int(safe_z)
                        ).location if hasattr(player.dimension, 'get_block') else loc
                    )

                    player.send_message(
                        f"§2[§7Paradox§2]§e You've reached the world border! "
                        f"(radius: {self._radius})"
                    )
            except Exception:
                pass

    def set_border(self, radius: int, center_x: int = 0, center_z: int = 0):
        """Update world border settings."""
        self._radius = radius
        self._center_x = center_x
        self._center_z = center_z
        self.db.set("config", "worldborder", {
            "radius": radius,
            "center_x": center_x,
            "center_z": center_z,
            "enabled": True,
        })
