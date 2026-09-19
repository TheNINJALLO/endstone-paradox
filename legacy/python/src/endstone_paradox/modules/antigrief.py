# antigrief.py - Anti-grief / world protection for Paradox AntiCheat
# Detects mass block breaking (nuking), rapid placement, and optionally
# tracks explosions.

import time
from collections import defaultdict, deque
from typing import Dict
from endstone_paradox.modules.base import BaseModule


class AntiGriefModule(BaseModule):
    """Anti-grief and world protection.

    Features:
      - Anti-nuke: flags players who break too many blocks too fast
      - Placement rate-limit: flags rapid block placement (scaffold-like griefing)
      - Explosion logging: tracks TNT/creeper/etc. explosions for audit
    """

    name = "antigrief"

    def on_start(self):
        self._break_limit = int(self.db.get("config", "antigrief_break_limit", 45))
        self._break_window = float(self.db.get("config", "antigrief_break_window", 3.0))
        self._place_limit = int(self.db.get("config", "antigrief_place_limit", 40))
        self._place_window = float(self.db.get("config", "antigrief_place_window", 3.0))
        self._log_explosions = self.db.get("config", "antigrief_log_explosions", True)

        # Consecutive-flag threshold before emitting violation
        self._nuke_flags_required = 2
        self._place_flags_required = 2

        # Per-player tracking
        self._breaks: Dict[str, deque] = defaultdict(lambda: deque(maxlen=200))
        self._places: Dict[str, deque] = defaultdict(lambda: deque(maxlen=200))
        self._nuke_flags: Dict[str, int] = defaultdict(int)
        self._place_flags: Dict[str, int] = defaultdict(int)

    @property
    def check_interval(self) -> int:
        return 0  # event-driven only

    def check(self):
        pass

    def _apply_sensitivity(self):
        self._break_limit = int(self._scale(45, invert=True))
        self._place_limit = int(self._scale(40, invert=True))

    # --- Block break handler ---

    def on_block_break(self, event):
        """Called from paradox.py on_block_break."""
        player = event.player
        if self.plugin.security.is_level4(player):
            return

        uuid_str = str(player.unique_id)
        now = time.time()

        self._breaks[uuid_str].append(now)

        # Count breaks in window
        recent = sum(1 for t in self._breaks[uuid_str]
                     if now - t < self._break_window)

        if recent >= self._break_limit:
            self._nuke_flags[uuid_str] += 1
            if self._nuke_flags[uuid_str] >= self._nuke_flags_required:
                # Get block info
                block_type = ""
                try:
                    block_type = str(event.block.type) if event.block else ""
                except Exception:
                    pass

                if hasattr(self.plugin, 'violation_engine'):
                    self.plugin.violation_engine.emit_violation(
                        player, "antigrief", 4, {
                            "type": "nuke",
                            "blocks_broken": recent,
                            "window": self._break_window,
                            "last_block": block_type,
                        }, "setback"
                    )
                self._nuke_flags[uuid_str] = 0
                # Cancel the break
                try:
                    event.cancelled = True
                except Exception:
                    pass
        else:
            self._nuke_flags[uuid_str] = 0

    # --- Block place handler ---

    def on_block_place(self, event):
        """Called from paradox.py on_block_place."""
        player = event.player
        if self.plugin.security.is_level4(player):
            return

        uuid_str = str(player.unique_id)
        now = time.time()

        self._places[uuid_str].append(now)

        # Count placements in window
        recent = sum(1 for t in self._places[uuid_str]
                     if now - t < self._place_window)

        if recent >= self._place_limit:
            self._place_flags[uuid_str] += 1
            if self._place_flags[uuid_str] >= self._place_flags_required:
                block_type = ""
                try:
                    block_type = str(event.block.type) if event.block else ""
                except Exception:
                    pass

                if hasattr(self.plugin, 'violation_engine'):
                    self.plugin.violation_engine.emit_violation(
                        player, "antigrief", 3, {
                            "type": "rapid_place",
                            "blocks_placed": recent,
                            "window": self._place_window,
                            "last_block": block_type,
                        }, "cancel"
                    )
                self._place_flags[uuid_str] = 0
                try:
                    event.cancelled = True
                except Exception:
                    pass
        else:
            self._place_flags[uuid_str] = 0

    # --- Explosion logging ---

    def on_explosion(self, source_type: str, location, dimension: str = ""):
        """Log an explosion event for audit trail."""
        if not self._log_explosions:
            return
        try:
            entry = {
                "source": source_type,
                "x": round(location.x, 1),
                "y": round(location.y, 1),
                "z": round(location.z, 1),
                "dim": dimension,
                "time": time.time(),
            }
            existing = self.db.get("logs", "explosions", [])
            if not isinstance(existing, list):
                existing = []
            existing.append(entry)
            # Keep last 500
            if len(existing) > 500:
                existing = existing[-500:]
            self.db.set("logs", "explosions", existing)
        except Exception:
            pass

    def on_player_leave(self, player):
        uuid_str = str(player.unique_id)
        self._breaks.pop(uuid_str, None)
        self._places.pop(uuid_str, None)
        self._nuke_flags.pop(uuid_str, None)
        self._place_flags.pop(uuid_str, None)
