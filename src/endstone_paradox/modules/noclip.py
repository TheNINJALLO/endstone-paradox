# noclip.py - NoClip / Phase detection
# Detects players walking through solid blocks by ray-tracing between positions.
# Only flags sustained *horizontal* phasing (walls/floors).  Normal jumps,
# stair climbing, slab walking, and water transitions are all exempt.

import time
import math
from endstone import GameMode
from endstone_paradox.modules.base import BaseModule


class NoClipModule(BaseModule):
    """Detects players phasing through solid blocks.

    Only triggers on sustained horizontal movement through walls.
    Exempt: jumping, climbing, stairs, slabs, water, knockback, etc.
    """

    name = "noclip"
    check_interval = 10  # 0.5 seconds

    PHASE_FLAGS_REQUIRED = 4  # base consecutive solid-path checks before flag
    WATER_GRACE_SECONDS = 3.0  # seconds of immunity after touching water

    # Blocks that look solid but are pass-through (substring match)
    PASSTHROUGH = {
        "air", "cave_air", "void_air",
        "water", "flowing_water", "lava", "flowing_lava",
        "bubble_column",
        # Partial / non-full blocks
        "slab", "stairs", "stair", "step",
        "wall", "fence", "fence_gate",
        "door", "trapdoor",
        "sign", "wall_sign", "hanging_sign",
        "torch", "soul_torch", "redstone_torch",
        "carpet", "snow_layer", "snow", "moss_carpet",
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
        "kelp", "seagrass", "tall_seagrass",
        "piston", "sticky_piston", "piston_head",
        "bed", "anvil", "enchanting_table", "brewing_stand",
        "chest", "trapped_chest", "ender_chest", "barrel",
        "hopper", "dropper", "dispenser",
        "bell", "grindstone", "stonecutter", "lectern",
        "campfire", "soul_campfire",
        "conduit", "end_portal_frame",
        "flower_pot", "decorated_pot",
        "turtle_egg", "frog_spawn",
        "pointed_dripstone", "amethyst_cluster",
        "small_amethyst_bud", "medium_amethyst_bud", "large_amethyst_bud",
        "lily_pad",
        "mushroom", "brown_mushroom", "red_mushroom",
        "sweet_berry", "cave_vine",
        "chorus_flower", "chorus_plant",
        "sculk_sensor", "sculk_shrieker", "sculk_catalyst",
    }

    # Substrings that indicate liquid/water-related blocks
    LIQUID_HINTS = ("water", "lava", "flowing", "bubble", "kelp", "seagrass")

    def on_start(self):
        self._player_data = {}
        self._recent_damage = {}

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
        """Check if a block type string represents a solid, full-size block."""
        name = block_type_str.lower().replace("minecraft:", "")
        for pt in self.PASSTHROUGH:
            if pt in name:
                return False
        return True

    def _is_liquid(self, block_type_str: str) -> bool:
        """Check if a block is water, lava, or any aquatic block."""
        name = block_type_str.lower().replace("minecraft:", "")
        for hint in self.LIQUID_HINTS:
            if hint in name:
                return True
        return False

    def _scan_for_liquid(self, dim, x: float, y: float, z: float) -> bool:
        """Check a 3x3x3 region around a position for any liquid blocks."""
        ix, iy, iz = int(x), int(y), int(z)
        for oy in (-1, 0, 1):
            for ox in (-1, 0, 1):
                for oz in (-1, 0, 1):
                    try:
                        bl = dim.get_block_at(ix + ox, iy + oy, iz + oz)
                        if bl is not None and self._is_liquid(str(bl.type)):
                            return True
                    except Exception:
                        pass
        return False

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
                    "water_until": 0.0,
                })

                prev = data["last_pos"]
                cur = (loc.x, loc.y, loc.z)
                data["last_pos"] = cur

                # Calculate movement deltas
                dx = cur[0] - prev[0]
                dy = cur[1] - prev[1]
                dz = cur[2] - prev[2]
                dist = math.sqrt(dx*dx + dy*dy + dz*dz)

                # ── Skip small movements ──
                if dist < 0.5:
                    data["phase_flags"] = max(0, data["phase_flags"] - 1)
                    continue

                # ── Vertical movement exemption ──
                # ANY vertical movement (jumping, falling, stairs, slabs)
                # means the player is NOT phasing through a wall.
                # Real noclip is purely horizontal (walking through walls).
                if abs(dy) > 0.1:
                    data["phase_flags"] = max(0, data["phase_flags"] - 1)
                    continue

                # ── Climbing exemption ──
                try:
                    if self.plugin.is_player_climbing(player):
                        data["phase_flags"] = 0
                        continue
                except Exception:
                    pass

                # ── Jump flag exemption ──
                try:
                    if self.plugin.is_player_jumping(player):
                        data["phase_flags"] = 0
                        continue
                except Exception:
                    pass

                # ── Water / liquid grace period ──
                dim = player.dimension
                near_liquid = (
                    self._scan_for_liquid(dim, cur[0], cur[1], cur[2]) or
                    self._scan_for_liquid(dim, prev[0], prev[1], prev[2])
                )

                if near_liquid:
                    data["water_until"] = now + self.WATER_GRACE_SECONDS
                    data["phase_flags"] = 0
                    continue

                if now < data["water_until"]:
                    data["phase_flags"] = 0
                    continue

                # ── Scale flags required by sensitivity ──
                # sens 1 → 12 flags, sens 2 → 10, sens 5 → 4, sens 10 → 2
                flags_needed = max(2, int(self.PHASE_FLAGS_REQUIRED * (12 - self.sensitivity) / 4))

                # ── Sample points along the horizontal path ──
                phase_detected = False
                for t in (0.33, 0.66):
                    sx = prev[0] + dx * t
                    sy = prev[1] + 0.1  # sample just above feet level
                    sz = prev[2] + dz * t

                    try:
                        block = dim.get_block_at(int(sx), int(sy), int(sz))
                        if block is not None:
                            block_type = str(block.type).lower()
                            if self._is_liquid(block_type):
                                data["water_until"] = now + self.WATER_GRACE_SECONDS
                                phase_detected = False
                                break
                            if self._is_solid(block_type):
                                phase_detected = True
                                break
                    except Exception:
                        pass

                # Record baseline (1.0 = phase hit, 0.0 = clear) to learn
                bl = self.record_baseline(
                    player, "noclip.phase_rate", 1.0 if phase_detected else 0.0
                )

                if phase_detected:
                    # During warmup, just learn — don't flag
                    if bl and bl.warming_up:
                        continue

                    data["phase_flags"] += 1
                    if data["phase_flags"] >= flags_needed:
                        # Only emit if baseline confirms abnormal phasing
                        if bl and bl.is_deviation:
                            self.emit(player, 4, {
                                "type": "noclip",
                                "distance": f"{dist:.1f}",
                                "z_score": bl.z_score,
                            }, action_hint="setback")
                        data["phase_flags"] = 0
                else:
                    data["phase_flags"] = max(0, data["phase_flags"] - 1)

            except Exception:
                pass
