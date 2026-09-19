# wallhit.py - Hit Through Walls (Line of Sight) detection
# Detects players hitting entities through solid blocks.

import math
from endstone_paradox.modules.base import BaseModule


class WallHitModule(BaseModule):
    """Detects hit-through-walls exploits.

    When a player deals damage, ray-traces from attacker's eye to
    victim's center.  If any solid block is in the way, the hit
    should not have connected — flag as wall-hit.
    """

    name = "wallhit"

    FLAGS_REQUIRED = 3  # consecutive wall-hits before flag

    # Non-solid blocks that don't block line of sight
    TRANSPARENT = {
        "air", "cave_air", "void_air",
        "water", "flowing_water", "lava", "flowing_lava",
        "glass", "stained_glass", "glass_pane", "stained_glass_pane",
        "iron_bars",
        "fence", "fence_gate",
        "door", "trapdoor",
        "sign", "wall_sign", "hanging_sign",
        "torch", "soul_torch", "redstone_torch",
        "carpet", "snow_layer",
        "pressure_plate", "button", "lever",
        "rail", "powered_rail", "detector_rail", "activator_rail",
        "flower", "sapling", "dead_bush", "fern", "grass",
        "tallgrass", "tall_grass",
        "vine", "ladder", "scaffolding", "cobweb", "web",
        "banner", "standing_banner", "wall_banner",
        "skull", "head",
        "end_rod", "chain", "lantern", "soul_lantern",
        "candle", "redstone_wire", "tripwire", "string",
        "leaves",  # leaves don't block hits
        "slab",    # half slabs may not block
    }

    def on_start(self):
        self._flags = {}  # uuid -> count

    def on_stop(self):
        self._flags.clear()

    def on_player_leave(self, player):
        self._flags.pop(str(player.unique_id), None)

    def _is_opaque(self, block_type_str: str) -> bool:
        """Check if a block type blocks line of sight."""
        name = block_type_str.lower().replace("minecraft:", "")
        for t in self.TRANSPARENT:
            if t in name:
                return False
        return True

    def on_damage(self, event):
        """Check line of sight from attacker to victim."""
        attacker = getattr(event, 'damager', None)
        victim = event.actor

        if attacker is None or victim is None:
            return
        if not hasattr(attacker, 'unique_id') or not hasattr(attacker, 'game_mode'):
            return
        if self.plugin.security.is_level4(attacker):
            return

        from endstone import GameMode
        if attacker.game_mode in (GameMode.CREATIVE, GameMode.SPECTATOR):
            return

        try:
            a_loc = attacker.location
            v_loc = victim.location
            if a_loc is None or v_loc is None:
                return

            # Ray from attacker eye to victim center
            eye_y = a_loc.y + 1.62  # eye height
            target_y = v_loc.y + 0.9  # ~center of entity

            dx = v_loc.x - a_loc.x
            dy = target_y - eye_y
            dz = v_loc.z - a_loc.z
            dist = math.sqrt(dx*dx + dy*dy + dz*dz)

            if dist < 1.0 or dist > 6.0:
                return  # too close (melee range) or too far

            dim = attacker.dimension
            steps = max(3, int(dist * 2))  # sample every 0.5 blocks

            blocked = False
            for i in range(1, steps):
                t = i / steps
                sx = a_loc.x + dx * t
                sy = eye_y + dy * t
                sz = a_loc.z + dz * t

                block = dim.get_block_at(int(sx), int(sy), int(sz))
                if block is not None:
                    bt = str(block.type).lower()
                    if self._is_opaque(bt):
                        blocked = True
                        break

            uuid_str = str(attacker.unique_id)

            if blocked:
                count = self._flags.get(uuid_str, 0) + 1
                self._flags[uuid_str] = count

                if count >= self.FLAGS_REQUIRED:
                    self.emit(attacker, 4, {
                        "type": "wall_hit",
                        "desc": f"Hit entity through solid blocks {count} times at {dist:.1f}b range",
                        "distance": f"{dist:.1f}",
                        "hits": count,
                    }, action_hint="cancel")
                    self._flags[uuid_str] = 0
            else:
                self._flags[uuid_str] = max(0, self._flags.get(uuid_str, 0) - 1)

        except Exception:
            pass
