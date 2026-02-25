"""
Paradox AntiCheat - Base Module

Abstract base class for all detection/feature modules.
Provides start/stop lifecycle, periodic task scheduling, and a
standard interface for event routing.
"""

from abc import ABC, abstractmethod


class BaseModule(ABC):
    """Abstract base class for all Paradox modules."""

    def __init__(self, plugin):
        """
        Initialize the module.

        Args:
            plugin: The ParadoxPlugin instance.
        """
        self.plugin = plugin
        self.db = plugin.db
        self.logger = plugin.logger
        self.running = False
        self._task = None

    @property
    @abstractmethod
    def name(self) -> str:
        """Module name identifier."""
        ...

    @property
    def check_interval(self) -> int:
        """Tick interval for periodic checks (20 ticks = 1 second). Override in subclass."""
        return 20  # Default 1 second

    def start(self):
        """Start the module."""
        if self.running:
            return
        self.running = True
        self.on_start()
        # Start periodic check if the module has one
        if hasattr(self, "check") and callable(self.check):
            self._schedule_check()

    def stop(self):
        """Stop the module."""
        was_running = self.running
        self.running = False
        self._task = None  # Let GC handle task cancellation
        if was_running:
            self.on_stop()

    def _schedule_check(self):
        """Schedule the periodic check task."""
        def run_check():
            if not self.running:
                return
            try:
                self.check()
            except Exception as e:
                self.logger.error(f"[Paradox] Module '{self.name}' check error: {e}")
            # Re-schedule
            if self.running:
                self._task = self.plugin.server.scheduler.run_task(
                    self.plugin, run_check, delay=self.check_interval
                )

        self._task = self.plugin.server.scheduler.run_task(
            self.plugin, run_check, delay=self.check_interval
        )

    def on_start(self):
        """Called when the module starts. Override for init logic."""
        pass

    def on_stop(self):
        """Called when the module stops. Override for cleanup logic."""
        pass

    def on_player_leave(self, player):
        """Called when a player leaves. Override to clean up per-player state."""
        pass

    def on_damage(self, event):
        """Called on ActorDamageEvent. Override in combat modules."""
        pass

    def on_block_break(self, event):
        """Called on BlockBreakEvent. Override in block modules."""
        pass

    def on_block_place(self, event):
        """Called on BlockPlaceEvent. Override in block modules."""
        pass

    def on_packet(self, event):
        """Called on PacketReceiveEvent. Override in packet modules."""
        pass

    def on_gamemode_change(self, event):
        """Called on PlayerGameModeChangeEvent. Override as needed."""
        pass

    def alert_admins(self, message: str):
        """Send an alert to all Level 4 players."""
        self.plugin.send_to_level4(f"§2[§7Paradox§2]§e {message}")
