# noclip.py - NoClip / Phase detection
# Detects players walking through solid blocks by ray-tracing between positions.

import time
import math
from endstone import GameMode
from endstone_paradox.modules.base import BaseModule


class NoClipModule(BaseModule):
    """Detects players phasing through solid blocks.

    Each tick, compares current position to last position and samples
    blocks along the movement path.  If any intermediate block is solid
    (and the player isn't in a door, trapdoor, fence gate, etc.),
    that's a noclip violation.
    """

    name = "noclip"
    check_interval = 10  # 0.5 seconds

    PHASE_FLAGS_REQUIRED = 3  # consecutive solid-path checks before flag

    # Blocks that look solid but are pass-through
    PASSTHROUGH = {
        "air", "cave_air", "void_air",
        "water", "flowing_water", "lava", "flowing_lava",
        "door", "trapdoor", "fence_gate",
        "sign", "wall_sign", "hanging_sign",
        "torch", "soul_torch", "redstone_torch",
        "carpet", "snow_layer", "moss_carpet",
        "pressure_plate", "button", "lever",
        "rail", "powered_rail", "detector_rail", "activator_rail",
        "flower", "sapling", "dead_bush", "fern", "grass",
        "tallgrass", "tall_grass", "large_fern",
        "vine", "ladder", "scaffolding",
        "banner", "standing_banner", "wall_banner",
        "cobweb", "web",
        "skull", "head",
        "end_rod", "chain", "lantern", "soul_lantern",
        "candle", "cake",
        "redstone_wire", "tripwire", "string",
        "structure_void", "barrier",
        "light_block",
    }

    def on_start(self):
        self._player_data = {}  # uuid -> {last_pos, phase_flags}
        self._recent_damage = {}  # uuid -> timestamp (knockback exemption)

    def on_stop(self):
        self._player_data.clear()
        self._recent_damage.clear()

    def on_player_leave(self, player):
        uuid_str = str(player.unique_id)
        self._player_data.pop(uuid_str, None)
        self._recent_damage.pop(uuid_str, None)

    def on_damage(self, event):
        """Track damage for knockback exemption."""
        victim = event.actor
        if victim and hasattr(victim, 'unique_id') and hasattr(victim, 'game_mode'):
            self._recent_damage[str(victim.unique_id)] = time.time()

    def _is_solid(self, block_type_str: str) -> bool:
        """Check if a block type string represents a solid block."""
        name = block_type_str.lower().replace("minecraft:", "")
        # Check passthrough list
        for pt in self.PASSTHROUGH:
            if pt in name:
                return False
        return True

    def check(self):
        now = time.time()
        for player in self.plugin.server.online_players:
            try:
                if player.game_mode in (GameMode.CREATIVE, GameMode.SPECTATOR):
                    continue
                if self.plugin.security.is_level4(player):
                    continue

                uuid_str = str(player.unique_id)

                # Knockback exemption (2s)
                if now - self._recent_damage.get(uuid_str, 0) < 2.0:
                    continue

                loc = player.location
                data = self._player_data.setdefault(uuid_str, {
                    "last_pos": (loc.x, loc.y, loc.z),
                    "phase_flags": 0,
                })

                prev = data["last_pos"]
                cur = (loc.x, loc.y, loc.z)
                data["last_pos"] = cur

                # Calculate distance moved
                dx = cur[0] - prev[0]
                dy = cur[1] - prev[1]
                dz = cur[2] - prev[2]
                dist = math.sqrt(dx*dx + dy*dy + dz*dz)

                # Skip tiny movements (< 0.2 blocks)
                if dist < 0.2:
                    data["phase_flags"] = max(0, data["phase_flags"] - 1)
                    continue

                # Sample 3 points along the path
                phase_detected = False
                for t in (0.25, 0.5, 0.75):
                    sx = prev[0] + dx * t
                    sy = prev[1] + dy * t + 0.5  # sample at chest height
                    sz = prev[2] + dz * t

                    try:
                        dim = player.dimension
                        block = dim.get_block_at(int(sx), int(sy), int(sz))
                        if block is not None:
                            block_type = str(block.type).lower()
                            if self._is_solid(block_type):
                                phase_detected = True
                                break
                    except Exception:
                        pass

                if phase_detected:
                    data["phase_flags"] += 1
                    if data["phase_flags"] >= self.PHASE_FLAGS_REQUIRED:
                        self.emit(player, 4, {
                            "type": "noclip",
                            "distance": f"{dist:.1f}",
                        }, action_hint="setback")
                        data["phase_flags"] = 0
                else:
                    data["phase_flags"] = max(0, data["phase_flags"] - 1)

            except Exception:
                pass
