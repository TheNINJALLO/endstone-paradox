# self_infliction.py - Detects self-damage exploit attempts

from endstone_paradox.modules.base import BaseModule


class SelfInflictionModule(BaseModule):
    """Detects self-infliction (self-damage) exploits."""

    name = "selfinfliction"

    def on_start(self):
        self._flags = {}  # UUID -> count

    def on_stop(self):
        self._flags.clear()

    def on_player_leave(self, player):
        self._flags.pop(str(player.unique_id), None)

    def on_damage(self, event):
        """Check for self-damage events."""
        actor = event.actor
        if actor is None or not hasattr(actor, 'unique_id'):
            return
        if not hasattr(actor, 'game_mode'):
            return

        # Check if the damager is the same as the damaged entity
        # This indicates a self-infliction attempt
        try:
            damager = getattr(event, 'damager', None)
            if damager is None:
                return
            if not hasattr(damager, 'unique_id'):
                return

            if str(actor.unique_id) == str(damager.unique_id):
                if self.plugin.security.is_level4(actor):
                    return

                uuid_str = str(actor.unique_id)
                count = self._flags.get(uuid_str, 0) + 1
                self._flags[uuid_str] = count

                event.is_cancelled = True

                if count >= 5:
                    self.emit(actor, 2, {
                        "count": count,
                    }, action_hint="cancel")
                    self._flags[uuid_str] = 0
        except Exception:
            pass
