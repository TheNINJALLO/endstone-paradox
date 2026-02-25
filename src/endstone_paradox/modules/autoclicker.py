# autoclicker.py - CPS-based autoclicker detection

import time
from collections import deque
from endstone_paradox.modules.base import BaseModule


class AutoClickerModule(BaseModule):
    """Detects autoclicker hacks via CPS monitoring."""

    name = "autoclicker"

    MAX_CPS = 30            # Maximum allowed clicks per second (high-end mice can do 20+)
    WINDOW_SIZE = 1.0       # Time window in seconds

    def on_start(self):
        self._click_data = {}  # UUID -> deque of timestamps
        # Load custom max CPS from config
        custom = self.db.get("config", "max_cps")
        if custom is not None:
            self.MAX_CPS = int(custom)

    def on_stop(self):
        self._click_data.clear()

    def on_player_leave(self, player):
        self._click_data.pop(str(player.unique_id), None)

    def on_damage(self, event):
        """Track attack frequency for CPS calculation."""
        actor = event.actor
        if actor is None or not hasattr(actor, 'unique_id'):
            return
        if not hasattr(actor, 'game_mode'):
            return
        if self.plugin.security.is_level4(actor):
            return

        uuid_str = str(actor.unique_id)
        now = time.time()

        clicks = self._click_data.setdefault(uuid_str, deque())
        clicks.append(now)

        # Remove clicks outside the window
        while clicks and (now - clicks[0]) > self.WINDOW_SIZE:
            clicks.popleft()

        cps = len(clicks)
        if cps > self.MAX_CPS:
            event.is_cancelled = True
            self.alert_admins(
                f"§c{actor.name}§e flagged for AutoClicker "
                f"(CPS={cps}, max={self.MAX_CPS})"
            )
            self._click_data[uuid_str].clear()
