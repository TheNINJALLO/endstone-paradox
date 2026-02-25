# base.py - Abstract base for all detection/feature modules

from abc import ABC, abstractmethod


class BaseModule(ABC):
    """Base class all Paradox modules inherit from. Handles start/stop
    lifecycle and optional periodic task scheduling."""

    def __init__(self, plugin):
        self.plugin = plugin
        self.db = plugin.db
        self.logger = plugin.logger
        self.running = False
        self._task = None

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    def check_interval(self) -> int:
        """Ticks between periodic checks. 20 ticks = 1 second."""
        return 20

    def start(self):
        if self.running:
            return
        self.running = True
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
    def on_player_leave(self, player): pass
    def on_damage(self, event): pass
    def on_block_break(self, event): pass
    def on_block_place(self, event): pass
    def on_packet(self, event): pass
    def on_gamemode_change(self, event): pass

    def alert_admins(self, message: str):
        self.plugin.send_to_level4(f"§2[§7Paradox§2]§e {message}")
