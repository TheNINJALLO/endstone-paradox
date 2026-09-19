# base.py - Abstract base for all detection/feature modules

from abc import ABC, abstractmethod


class BaseModule(ABC):
    """Base class all Paradox modules inherit from. Handles start/stop
    lifecycle, optional periodic task scheduling, and sensitivity control."""

    # Sensitivity scale: 1 (lenient) → 5 (default) → 10 (strict)
    DEFAULT_SENSITIVITY = 5
    MIN_SENSITIVITY = 1
    MAX_SENSITIVITY = 10

    def __init__(self, plugin):
        self.plugin = plugin
        self.db = plugin.db
        self.logger = plugin.logger
        self.running = False
        self._task = None
        self._sensitivity = self.DEFAULT_SENSITIVITY

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    def check_interval(self) -> int:
        """Ticks between periodic checks. 20 ticks = 1 second."""
        return 20

    @property
    def sensitivity(self) -> int:
        return self._sensitivity

    def set_sensitivity(self, level: int):
        """Set sensitivity (1-10) and persist to DB."""
        level = max(self.MIN_SENSITIVITY, min(self.MAX_SENSITIVITY, level))
        self._sensitivity = level
        self.db.set("config", f"sensitivity_{self.name}", level)
        self._apply_sensitivity()

    def _load_sensitivity(self):
        """Load sensitivity from DB, falling back to default."""
        stored = self.db.get("config", f"sensitivity_{self.name}")
        if stored is not None:
            self._sensitivity = max(self.MIN_SENSITIVITY, min(self.MAX_SENSITIVITY, int(stored)))
        else:
            self._sensitivity = self.DEFAULT_SENSITIVITY
        self._apply_sensitivity()

    def _apply_sensitivity(self):
        """Override in subclasses to recalculate thresholds based on self._sensitivity.
        Called after sensitivity changes. Default implementation does nothing."""
        pass

    def _scale(self, base_value: float, invert: bool = False) -> float:
        """Scale a threshold value based on current sensitivity.

        Args:
            base_value: The value at sensitivity 5 (default).
            invert: If True, higher sensitivity = higher value (e.g. for counts/limits).
                    If False, higher sensitivity = lower value (e.g. for thresholds/tolerances).

        Returns the scaled value.
        """
        # Maps sensitivity 1→2.0x, 5→1.0x, 10→0.33x (or inverted)
        factor = 1.0 + (5 - self._sensitivity) * 0.2
        factor = max(0.33, min(2.0, factor))
        if invert:
            # Higher sensitivity = higher value (stricter counts, more detections)
            return base_value / factor
        else:
            # Higher sensitivity = lower value (tighter tolerances)
            return base_value * factor

    def start(self):
        if self.running:
            return
        self.running = True
        self._load_sensitivity()
        self.on_start()
        if hasattr(self, "check") and callable(self.check):
            self._schedule_check()

    def stop(self):
        was_running = self.running
        self.running = False
        self._task = None
        if was_running:
            self.on_stop()

    def _schedule_check(self):
        def run_check():
            if not self.running:
                return
            try:
                self.check()
            except Exception as e:
                self.logger.error(f"[Paradox] Module '{self.name}' check error: {e}")
            if self.running:
                self._task = self.plugin.server.scheduler.run_task(
                    self.plugin, run_check, delay=self.check_interval
                )

        self._task = self.plugin.server.scheduler.run_task(
            self.plugin, run_check, delay=self.check_interval
        )

    # -- override points --
    def on_start(self): pass
    def on_stop(self): pass
    def on_player_join(self, player): pass
    def on_player_leave(self, player): pass
    def on_damage(self, event): pass
    def on_move(self, event): pass
    def on_block_break(self, event): pass
    def on_block_place(self, event): pass
    def on_packet(self, event): pass
    def on_gamemode_change(self, event): pass

    def alert_admins(self, message: str):
        self.plugin.send_to_level4(f"§2[§7Paradox§2]§e {message}")

    def emit(self, player, severity: int, evidence: dict,
             action_hint: str = None):
        """Emit a violation to the centralised engine."""
        engine = getattr(self.plugin, 'violation_engine', None)
        if engine:
            engine.emit_violation(player, self.name, severity, evidence, action_hint)
        else:
            # Fallback if engine not yet initialised
            ev_str = ', '.join(f'{k}={v}' for k, v in evidence.items())
            name = getattr(player, 'name', '?')
            self.alert_admins(f"§c{name}§e {self.name} ({ev_str})")

    def record_baseline(self, player, metric: str, value: float):
        """Record a metric sample to the player's behavioral baseline.

        Returns DeviationResult or None if baseline not available.
        """
        baseline = getattr(self.plugin, 'player_baseline', None)
        if baseline is None:
            return None
        uuid_str = str(player.unique_id) if hasattr(player, 'unique_id') else None
        if uuid_str is None:
            return None
        return baseline.record(uuid_str, metric, value)
