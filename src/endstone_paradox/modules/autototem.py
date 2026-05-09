import time
from endstone_paradox.modules.base import BaseModule

class AutoTotemModule(BaseModule):
    """Detects inhuman Totem of Undying replenishment."""

    name = "autototem"
    TICK_THRESHOLD = 5 # 5 ticks = 250ms

    def on_start(self):
        self._track = {} # uuid -> {totem_count, last_drop_tick}
        self._current_tick = 0
        self._run_task = True
        self._loop_task()

    def on_stop(self):
        self._run_task = False
        self._track.clear()

    def on_player_leave(self, player):
        self._track.pop(str(player.unique_id), None)

    def _loop_task(self):
        if not self._run_task:
            return

        self._current_tick += 1

        for player in self.plugin.server.online_players:
            if self.plugin.security.is_level4(player):
                continue
            
            uid = str(player.unique_id)
            inv = player.inventory
            if not inv:
                continue

            current_totems = 0
            # Track offhand if possible, otherwise count all totems
            # If player.inventory has item_in_off_hand, we could check it.
            # But let's just count total totems in inventory.
            for i in range(inv.size):
                item = inv.get_item(i)
                if item and "totem_of_undying" in str(item.type):
                    current_totems += item.amount
                    
            if hasattr(inv, 'item_in_off_hand'):
                off_item = inv.item_in_off_hand
                if off_item and "totem_of_undying" in str(off_item.type):
                    current_totems += off_item.amount

            data = self._track.get(uid)
            if not data:
                self._track[uid] = {"totem_count": current_totems, "last_drop_tick": 0}
                continue

            if current_totems < data["totem_count"]:
                # Totem popped or dropped
                data["last_drop_tick"] = self._current_tick
            elif current_totems > data["totem_count"]:
                # Totem replenished
                ticks_since_drop = self._current_tick - data["last_drop_tick"]
                if data["last_drop_tick"] > 0 and ticks_since_drop <= self.TICK_THRESHOLD:
                    # Inhuman replenishment
                    self.emit(player, 3, {
                        "type": "autototem",
                        "desc": f"Replenished totem in {ticks_since_drop} ticks"
                    }, action_hint="kick")
                    
                    # Mitigation: remove the newly equipped totem
                    self._remove_one_totem(inv)
                    current_totems -= 1

            data["totem_count"] = current_totems

        self.plugin.server.scheduler.run_task(self.plugin, self._loop_task, delay=1)

    def _remove_one_totem(self, inv):
        # Prefer offhand
        if hasattr(inv, 'item_in_off_hand'):
            item = inv.item_in_off_hand
            if item and "totem_of_undying" in str(item.type):
                if item.amount > 1:
                    item.amount -= 1
                    inv.item_in_off_hand = item
                else:
                    inv.item_in_off_hand = None
                return

        for i in range(inv.size):
            item = inv.get_item(i)
            if item and "totem_of_undying" in str(item.type):
                if item.amount > 1:
                    item.amount -= 1
                    inv.set_item(i, item)
                else:
                    inv.set_item(i, None) # Or air
                return
