# fly.py - Flight/hover detection with surrounding block validation
# Checks 8 surrounding blocks below to ensure majority are air before flagging.
# Validates player is within dimension height range.

import math
from endstone import GameMode
from endstone_paradox.modules.base import BaseModule


class FlyModule(BaseModule):
    name = "fly"
    check_interval = 20  # 1s

    # Base thresholds (at sensitivity 5)
    BASE_V_THRESHOLD = 0.15
    BASE_H_THRESHOLD = 0.15
    BASE_HOVER_THRESHOLD = 2  # seconds
    BASE_SPEED_THRESHOLD = 7.3  # blocks/second — sprint cap ~5.6, generous for latency

    def on_start(self):
        self._player_data = {}  # uuid -> {landing, hover_time, trident_used}
        self._recent_damage = {}  # uuid -> last_damage_time (knockback exemption)
        self._apply_sensitivity()

    def _apply_sensitivity(self):
        self.v_threshold = self._scale(self.BASE_V_THRESHOLD)
        self.h_threshold = self._scale(self.BASE_H_THRESHOLD)
        self.hover_threshold = self._scale(self.BASE_HOVER_THRESHOLD)
        self.speed_threshold = self._scale(self.BASE_SPEED_THRESHOLD)

    def on_stop(self):
        self._player_data.clear()
        self._recent_damage.clear()

    def on_player_leave(self, player):
        uuid_str = str(player.unique_id)
        self._player_data.pop(uuid_str, None)
        self._recent_damage.pop(uuid_str, None)

    def on_damage(self, event):
        """Track when player takes damage for knockback exemption."""
        victim = event.actor
        if victim is None or not hasattr(victim, 'unique_id'):
            return
        if hasattr(victim, 'game_mode'):
            import time as _t
            self._recent_damage[str(victim.unique_id)] = _t.time()

    def check(self):
        for player in self.plugin.server.online_players:
            try:
                self._check_player(player)
            except Exception:
                pass

    def _check_player(self, player):
        uuid_str = str(player.unique_id)

        # skip creative/spectator/admins
        if player.game_mode in (GameMode.CREATIVE, GameMode.SPECTATOR):
            return
        if self.plugin.security.is_level4(player):
            return

        if player.is_gliding or player.is_in_water:
            return
        if self.plugin.is_player_climbing(player):
            return

        # Falling exemption — significant downward velocity = gravity, not flying
        vel = player.velocity
        if vel.y < -0.5:
            return

        # Knockback exemption — 2s after taking damage
        import time as _t
        last_dmg = self._recent_damage.get(uuid_str, 0)
        if _t.time() - last_dmg < 2.0:
            return

        # Slime/honey block exemption
        if self._on_bouncy_block(player):
            return

        data = self._player_data.setdefault(uuid_str, {
            "landing": None,
            "hover_time": 0,
            "trident_used": False,
            "last_pos": None,
            "last_time": 0,
            "speed_flags": 0,
        })

        # trident riptide exemption
        if data["trident_used"]:
            data["trident_used"] = False
            data["last_pos"] = None  # reset speed tracking after riptide
            return

        loc = player.location
        now = _t.time()

        # ── Speed hack detection (works on ground AND in air) ──
        if data["last_pos"] is not None and data["last_time"] > 0:
            dt = now - data["last_time"]
            if 0.05 < dt < 5.0:  # sane time delta
                prev = data["last_pos"]
                dx = loc.x - prev[0]
                dz = loc.z - prev[1]
                h_dist = math.sqrt(dx * dx + dz * dz)
                h_speed_bps = h_dist / dt  # blocks per second

                # Always record baseline (ground and air) to learn normal speeds
                speed_bl = self.record_baseline(player, "fly.ground_speed", h_speed_bps)

                # Only flag if baseline is warmed up and this is a deviation
                if h_speed_bps > self.speed_threshold:
                    # During warmup, just learn — don't flag
                    if speed_bl and speed_bl.warming_up:
                        pass
                    else:
                        data["speed_flags"] += 1
                        if data["speed_flags"] >= 3:
                            # Only emit if baseline confirms deviation
                            if speed_bl and speed_bl.is_deviation:
                                severity = 4
                                evidence = {
                                    "speed": f"{h_speed_bps:.1f}",
                                    "max": f"{self.speed_threshold:.1f}",
                                    "type": "speed_hack",
                                    "baseline_avg": f"{speed_bl.avg:.1f}",
                                    "z_score": speed_bl.z_score,
                                }
                                self.emit(player, severity, evidence, action_hint="setback")
                            data["speed_flags"] = 0
                else:
                    data["speed_flags"] = max(0, data["speed_flags"] - 1)

        data["last_pos"] = (loc.x, loc.z)
        data["last_time"] = now

        if player.is_on_ground:
            data["landing"] = loc
            data["hover_time"] = 0
            return

        # recently jumped = legit air time
        if self.plugin.is_player_jumping(player):
            return

        # ── Surrounding block check ──
        # Check 8 blocks below + center for air majority
        # Avoids false positives near stairs, edges, half-slabs
        if not self._majority_air_below(player):
            data["hover_time"] = 0
            return

        vel = player.velocity
        h_speed = math.sqrt(vel.x ** 2 + vel.z ** 2)

        # Skip if falling (negative Y velocity = gravity, not hover)
        if vel.y < -0.3:
            data["hover_time"] = 0
            return

        is_suspicious = (
            (player.is_flying and not player.is_on_ground) or
            (vel.y >= self.v_threshold or h_speed >= self.h_threshold)
        )

        # Record baseline metrics (always, even when not suspicious — to learn)
        h_bl = self.record_baseline(player, "fly.h_speed", h_speed)

        if is_suspicious and not player.is_on_ground:
            data["hover_time"] += 1

            if data["hover_time"] >= self.hover_threshold:
                hover_bl = self.record_baseline(
                    player, "fly.hover_time", float(data["hover_time"])
                )

                # Only emit if baseline is past warmup
                if hover_bl and hover_bl.warming_up:
                    data["hover_time"] = 0  # reset but don't flag
                elif hover_bl and hover_bl.is_deviation:
                    self.emit(player, 4, {
                        "hover": data["hover_time"],
                        "threshold": self.hover_threshold,
                        "baseline_avg": f"{hover_bl.avg:.1f}",
                        "z_score": hover_bl.z_score,
                    }, action_hint="setback")
                    data["hover_time"] = 0
                else:
                    # Past warmup but not a deviation — normal hover, reset
                    data["hover_time"] = 0
        else:
            data["hover_time"] = max(0, data["hover_time"] - 1)

    def _majority_air_below(self, player):
        """
        Check if the majority of the 9 blocks below the player
        (center + 8 surrounding) are air. Returns True if majority air.
        Only flags fly if player is genuinely over open air.
        """
        try:
            loc = player.location
            dim = player.dimension

            # Validate within dimension height range
            try:
                height_range = dim.height_range if hasattr(dim, 'height_range') else None
                if height_range:
                    if loc.y < height_range[0] or loc.y >= height_range[1]:
                        return False
            except Exception:
                pass

            # Get block at player's feet, then check below it
            block_at = dim.get_block_at(int(loc.x), int(loc.y) - 1, int(loc.z))
            if block_at is None:
                return False

            air_count = 0
            total = 0
            offsets = [
                (0, 0), (1, 0), (-1, 0), (0, 1), (0, -1),
                (1, 1), (1, -1), (-1, 1), (-1, -1)
            ]

            for dx, dz in offsets:
                try:
                    check_block = dim.get_block_at(
                        int(loc.x) + dx, int(loc.y) - 1, int(loc.z) + dz
                    )
                    total += 1
                    if check_block is not None:
                        block_id = str(check_block.type).lower()
                        if "air" in block_id:
                            air_count += 1
                    else:
                        air_count += 1
                except Exception:
                    total += 1
                    air_count += 1  # Can't check = assume air

            # Majority (>50%) must be air to flag
            return air_count > total / 2

        except Exception:
            return False

    def set_trident_used(self, player):
        uuid_str = str(player.unique_id)
        data = self._player_data.get(uuid_str)
        if data:
            data["trident_used"] = True

    def _on_bouncy_block(self, player):
        """Check if player is on or near slime/honey blocks."""
        try:
            loc = player.location
            if loc is None:
                return False
            dim = player.dimension
            block = dim.get_block_at(int(loc.x), int(loc.y) - 1, int(loc.z))
            if block is not None:
                block_id = str(block.type).lower()
                if "slime" in block_id or "honey" in block_id:
                    return True
        except Exception:
            pass
        return False
