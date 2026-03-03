# skinguard.py - Skin validation (4D geometry, tiny/invisible skins)

import json
import time
from endstone_paradox.modules.base import BaseModule


class SkinGuardModule(BaseModule):
    """Detects and rejects invalid skins: 4D geometry, tiny models,
    invisible/transparent skins, and non-standard dimensions."""

    name = "skinguard"

    # Valid Bedrock geometry models
    VALID_GEOMETRY = frozenset({
        "geometry.humanoid.custom",
        "geometry.humanoid.customslim",
        "geometry.humanoid",
        "geometry.humanoid.custom.baby",
        "geometry.humanoid.customslim.baby",
        "geometry.cape",
    })

    # Valid skin texture sizes (width × height)
    VALID_DIMENSIONS = frozenset({
        (64, 32),
        (64, 64),
        (128, 128),
        (256, 256),   # HD skins (some marketplace)
    })

    # Minimum expected bones in a valid player model
    MIN_BONES = 4  # head, body, leftArm, rightArm at minimum

    # Minimum expected model volume (sum of cube sizes)
    MIN_TOTAL_VOLUME = 500  # standard Steve ≈ 2000+ volume units

    # Transparency threshold — fraction of pixels that can be fully transparent
    MAX_TRANSPARENT_RATIO = 0.95  # if >95% transparent → invisible skin

    # Minimum visible pixels (at least some part of the skin must be visible)
    MIN_VISIBLE_PIXELS = 50

    # Cooldown per player to avoid spam on reconnect
    _check_cooldown = {}

    def on_start(self):
        self._check_cooldown = {}

    def on_stop(self):
        self._check_cooldown.clear()

    def on_player_leave(self, player):
        uid = str(getattr(player, 'unique_id', ''))
        self._check_cooldown.pop(uid, None)

    def check_player(self, player) -> bool:
        """Validate a player's skin on join.

        Returns True if the skin passes all checks, False if rejected.
        """
        uid = str(getattr(player, 'unique_id', ''))
        now = time.time()

        # Cooldown — don't recheck within 5 seconds (reconnect spam)
        if uid in self._check_cooldown and now - self._check_cooldown[uid] < 5:
            return True
        self._check_cooldown[uid] = now

        # Get the skin object safely
        skin = getattr(player, 'skin', None)
        if skin is None:
            return True  # Can't check if API doesn't expose it

        violations = []

        # ── Check 1: Geometry name ──────────────────────────────
        violations.extend(self._check_geometry_name(skin))

        # ── Check 2: Geometry data (bone/cube validation) ───────
        violations.extend(self._check_geometry_data(skin))

        # ── Check 3: Transparency / invisible skin ──────────────
        violations.extend(self._check_transparency(skin))

        # ── Check 4: Texture dimensions ─────────────────────────
        violations.extend(self._check_dimensions(skin))

        # ── Handle violations ───────────────────────────────────
        if violations:
            reasons = ", ".join(violations)
            self.emit(player, 4, {
                "reasons": reasons,
                "skin_id": getattr(skin, 'skin_id', 'unknown'),
            }, action_hint="kick")

            try:
                player.kick(f"§c[Paradox] Invalid skin: {reasons}")
            except Exception:
                pass

            self._log_skin_violation(player, violations)
            return False

        return True

    # ── Geometry name validation ────────────────────────────────

    def _check_geometry_name(self, skin) -> list[str]:
        """Verify the skin uses a standard Bedrock geometry model."""
        geo_name = getattr(skin, 'geometry_name', None)
        if geo_name is None:
            # Try alternate attribute names
            geo_name = getattr(skin, 'geometry', None)
        if geo_name is None:
            return []  # Can't check — API may not expose it

        geo_lower = str(geo_name).lower().strip()

        # Empty geometry name is fine (uses default)
        if not geo_lower:
            return []

        # Check against known valid names
        if geo_lower in self.VALID_GEOMETRY:
            return []

        # Allow any name that starts with a valid prefix (some versions append hashes)
        for valid in self.VALID_GEOMETRY:
            if geo_lower.startswith(valid):
                return []

        return [f"non-standard geometry: {geo_name}"]

    # ── Geometry data (bone/cube) validation ────────────────────

    def _check_geometry_data(self, skin) -> list[str]:
        """Parse geometry JSON and validate bone structure."""
        geo_data = getattr(skin, 'geometry_data', None)
        if geo_data is None:
            geo_data = getattr(skin, 'geometry_data_engine_version', None)
        if not geo_data:
            return []  # No custom geometry = default model = OK

        try:
            parsed = json.loads(geo_data) if isinstance(geo_data, str) else geo_data
        except (json.JSONDecodeError, TypeError):
            return ["corrupt geometry data"]

        violations = []

        # Handle both old format {"bones": [...]} and new format
        # {"minecraft:geometry": [{"bones": [...]}]}
        geometries = []
        if isinstance(parsed, dict):
            if "minecraft:geometry" in parsed:
                geometries = parsed["minecraft:geometry"]
            elif "bones" in parsed:
                geometries = [parsed]
            elif isinstance(parsed, list):
                geometries = parsed
            else:
                # Try to find any key containing geometry data
                for key, val in parsed.items():
                    if isinstance(val, list):
                        for item in val:
                            if isinstance(item, dict) and "bones" in item:
                                geometries.append(item)

        if not geometries:
            return []  # No parseable geometry

        for geo in geometries:
            if not isinstance(geo, dict):
                continue

            bones = geo.get("bones", [])
            if not isinstance(bones, list):
                continue

            # Check bone count
            if len(bones) < self.MIN_BONES:
                violations.append(f"too few bones ({len(bones)})")

            # Check cube sizes — calculate total model volume
            total_volume = 0
            has_tiny_cubes = False

            for bone in bones:
                if not isinstance(bone, dict):
                    continue
                cubes = bone.get("cubes", [])
                if not isinstance(cubes, list):
                    continue
                for cube in cubes:
                    if not isinstance(cube, dict):
                        continue
                    size = cube.get("size", [0, 0, 0])
                    if isinstance(size, list) and len(size) >= 3:
                        try:
                            vol = abs(float(size[0])) * abs(float(size[1])) * abs(float(size[2]))
                            total_volume += vol
                            # Flag extremely tiny cubes (< 0.5 pixels in any dimension)
                            if any(abs(float(s)) < 0.5 for s in size[:3]):
                                has_tiny_cubes = True
                        except (ValueError, TypeError):
                            pass

            if total_volume > 0 and total_volume < self.MIN_TOTAL_VOLUME:
                violations.append(f"model too small (vol={total_volume:.0f})")

            if has_tiny_cubes:
                violations.append("sub-pixel bone dimensions")

        return violations

    # ── Transparency / invisible skin detection ─────────────────

    def _check_transparency(self, skin) -> list[str]:
        """Check if the skin texture is mostly transparent (invisible)."""
        skin_data = getattr(skin, 'skin_data', None)
        if skin_data is None:
            skin_data = getattr(skin, 'data', None)
        if not skin_data:
            return []

        # skin_data should be raw RGBA bytes (4 bytes per pixel)
        try:
            if isinstance(skin_data, (bytes, bytearray)):
                pixel_data = skin_data
            elif isinstance(skin_data, str):
                # Base64 encoded
                import base64
                pixel_data = base64.b64decode(skin_data)
            else:
                return []
        except Exception:
            return []

        if len(pixel_data) < 16:
            return []  # Too small to be a real skin

        total_pixels = len(pixel_data) // 4
        if total_pixels == 0:
            return []

        # Count transparent pixels (alpha channel is every 4th byte, offset 3)
        transparent_count = 0
        for i in range(3, len(pixel_data), 4):
            if pixel_data[i] < 10:  # Alpha < 10 = effectively invisible
                transparent_count += 1

        visible = total_pixels - transparent_count
        ratio = transparent_count / total_pixels

        violations = []
        if ratio > self.MAX_TRANSPARENT_RATIO:
            violations.append(f"invisible skin ({ratio:.0%} transparent)")
        elif visible < self.MIN_VISIBLE_PIXELS:
            violations.append(f"near-invisible skin ({visible} visible pixels)")

        return violations

    # ── Texture dimension validation ────────────────────────────

    def _check_dimensions(self, skin) -> list[str]:
        """Validate skin texture dimensions."""
        width = getattr(skin, 'skin_width', None) or getattr(skin, 'width', None)
        height = getattr(skin, 'skin_height', None) or getattr(skin, 'height', None)

        if width is None or height is None:
            # Try inferring from data length
            skin_data = getattr(skin, 'skin_data', None) or getattr(skin, 'data', None)
            if skin_data and isinstance(skin_data, (bytes, bytearray)):
                pixel_count = len(skin_data) // 4
                # Common sizes
                dim_map = {2048: (64, 32), 4096: (64, 64), 16384: (128, 128), 65536: (256, 256)}
                dims = dim_map.get(pixel_count)
                if dims:
                    width, height = dims
                else:
                    return []  # Can't determine
            else:
                return []

        try:
            w, h = int(width), int(height)
        except (ValueError, TypeError):
            return []

        if (w, h) not in self.VALID_DIMENSIONS:
            return [f"non-standard skin size ({w}×{h})"]

        return []

    # ── Logging ─────────────────────────────────────────────────

    def _log_skin_violation(self, player, violations: list[str]):
        """Log a skin violation to the database."""
        entry = {
            "name": player.name,
            "uuid": str(getattr(player, 'unique_id', '')),
            "violations": violations,
            "time": time.time(),
        }
        count = self.db.count("skin_log")
        self.db.set("skin_log", str(count + 1), entry)
