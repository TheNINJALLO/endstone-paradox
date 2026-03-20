# session_fingerprint.py - Session Fingerprinting (Tier 3)
# Device fingerprinting for alt account detection and ban evasion tracking.

import hashlib
import time
from endstone_paradox.modules.base import BaseModule


class SessionFingerprintModule(BaseModule):
    """Creates device-based fingerprints for players and detects alt accounts.

    On each join, collects available device metadata, creates a composite
    fingerprint hash, cross-checks against stored fingerprints to detect
    alt accounts, and checks for ban evasion.
    """

    @property
    def name(self) -> str:
        return "fingerprint"

    @property
    def check_interval(self) -> int:
        return 0  # No periodic check needed — event-driven only

    def on_start(self):
        self.db._ensure_table("fingerprints")
        self.db._ensure_table("trusted_links")

    def on_player_join(self, player):
        uuid_str = str(player.unique_id)
        now = time.time()

        # Collect available metadata
        metadata = self._collect_metadata(player)
        fingerprint_hash = self._create_fingerprint(metadata)

        # Load or create fingerprint record
        existing = self.db.get("fingerprints", uuid_str, {})
        if not isinstance(existing, dict):
            existing = {}

        # Update record
        existing["uuid"] = uuid_str
        existing["name"] = player.name
        existing["fingerprint"] = fingerprint_hash
        existing["ip"] = metadata.get("ip", "unknown")
        existing["device_os"] = metadata.get("device_os", "unknown")
        existing["xuid"] = metadata.get("xuid", "")
        existing["last_seen"] = now
        if "first_seen" not in existing:
            existing["first_seen"] = now
        if "linked_uuids" not in existing:
            existing["linked_uuids"] = []

        self.db.set("fingerprints", uuid_str, existing)

        # Cross-check for alt accounts (local)
        self._check_alts(player, uuid_str, fingerprint_hash, metadata)

        # Check for ban evasion (local)
        self._check_ban_evasion(player, uuid_str, existing)

        # Cross-check against Global Intelligence Network
        self._check_global_intelligence(player, fingerprint_hash, existing)

        # Push fingerprint to global network for crowd-sourced learning
        self._push_to_global(fingerprint_hash, existing)

    def _collect_metadata(self, player) -> dict:
        """Collect available device metadata from the player object."""
        metadata = {}

        # IP address
        try:
            addr = getattr(player, 'address', None)
            if addr:
                metadata["ip"] = str(addr).split(":")[0] if ":" in str(addr) else str(addr)
        except Exception:
            pass

        # Device OS / platform
        try:
            device_os = getattr(player, 'device_os', None)
            if device_os is not None:
                metadata["device_os"] = str(device_os)
        except Exception:
            pass

        # Device ID (if available)
        try:
            device_id = getattr(player, 'device_id', None)
            if device_id:
                metadata["device_id"] = str(device_id)
        except Exception:
            pass

        # XUID (Xbox User ID)
        try:
            xuid = getattr(player, 'xuid', None)
            if xuid:
                metadata["xuid"] = str(xuid)
        except Exception:
            pass

        # Player name (always available)
        metadata["name"] = player.name

        return metadata

    def _create_fingerprint(self, metadata: dict) -> str:
        """Create a composite hash from available metadata."""
        # Use stable components for fingerprinting
        components = []

        # IP is a strong signal but can change — include it anyway
        if "ip" in metadata:
            components.append(f"ip:{metadata['ip']}")

        # Device OS is stable
        if "device_os" in metadata:
            components.append(f"os:{metadata['device_os']}")

        # Device ID is the strongest signal (if available)
        if "device_id" in metadata:
            components.append(f"did:{metadata['device_id']}")

        # XUID is unique per Xbox account
        if "xuid" in metadata:
            components.append(f"xuid:{metadata['xuid']}")

        if not components:
            # Fallback — just use the name (weak fingerprint)
            components.append(f"name:{metadata.get('name', 'unknown')}")

        raw = "|".join(sorted(components))
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _check_alts(self, player, uuid_str: str, fingerprint: str, metadata: dict):
        """Cross-check fingerprint against all stored fingerprints for alt detection."""
        all_fingerprints = self.db.get_all("fingerprints")
        matches = []

        for stored_uuid, stored_data in all_fingerprints.items():
            if stored_uuid == uuid_str:
                continue
            if not isinstance(stored_data, dict):
                continue

            # Skip trusted pairs (family/household exemptions)
            if self.is_trusted_pair(uuid_str, stored_uuid):
                continue

            # Check fingerprint hash match
            if stored_data.get("fingerprint") == fingerprint:
                matches.append(stored_data)
                continue

            # Also check IP match (weaker signal but still useful)
            if (metadata.get("ip") and
                stored_data.get("ip") == metadata["ip"] and
                metadata["ip"] != "unknown"):
                matches.append(stored_data)

        if matches:
            # Update linked_uuids
            current_record = self.db.get("fingerprints", uuid_str, {})
            if isinstance(current_record, dict):
                linked = set(current_record.get("linked_uuids", []))
                for match in matches:
                    linked.add(match.get("uuid", ""))
                    # Also update the other record's linked list
                    other_uuid = match.get("uuid")
                    if other_uuid:
                        other_record = self.db.get("fingerprints", other_uuid, {})
                        if isinstance(other_record, dict):
                            other_linked = set(other_record.get("linked_uuids", []))
                            other_linked.add(uuid_str)
                            other_record["linked_uuids"] = list(other_linked)
                            self.db.set("fingerprints", other_uuid, other_record)

                linked.discard("")  # Remove empty strings
                current_record["linked_uuids"] = list(linked)
                self.db.set("fingerprints", uuid_str, current_record)

            # Alert admins
            match_names = [m.get("name", "?") for m in matches[:5]]
            self.alert_admins(
                f"§e🔍 Alt detection: §c{player.name}§e may be an alt of: "
                f"§f{', '.join(match_names)}"
            )

            self.emit(player, severity=2, evidence={
                "type": "alt_detection",
                "linked_accounts": match_names,
                "fingerprint": fingerprint[:8],
                "desc": f"Matching fingerprint with {len(matches)} other account(s)",
            })

    def _check_ban_evasion(self, player, uuid_str: str, fingerprint_record: dict):
        """Check if any linked UUIDs are banned — indicates ban evasion."""
        linked = fingerprint_record.get("linked_uuids", [])
        if not linked:
            return

        for linked_uuid in linked:
            # Skip trusted pairs (family/household exemptions)
            if self.is_trusted_pair(uuid_str, linked_uuid):
                continue
            ban_data = self.db.get("bans", linked_uuid)
            if ban_data is None:
                # Also check by name in the linked fingerprint
                linked_fp = self.db.get("fingerprints", linked_uuid, {})
                if isinstance(linked_fp, dict):
                    linked_name = linked_fp.get("name", "")
                    if linked_name:
                        ban_data = self.db.get("bans", linked_name.lower())

            if ban_data:
                linked_fp = self.db.get("fingerprints", linked_uuid, {})
                banned_name = linked_fp.get("name", linked_uuid[:8]) if isinstance(linked_fp, dict) else linked_uuid[:8]

                self.emit(player, severity=5, evidence={
                    "type": "ban_evasion",
                    "banned_account": banned_name,
                    "banned_uuid": linked_uuid,
                    "desc": f"Alt of banned player: {banned_name}",
                }, action_hint="ban")

                self.alert_admins(
                    f"§c⚠ BAN EVASION: §c{player.name}§e is linked to "
                    f"banned player §c{banned_name}§e!"
                )

                # Auto-kick for ban evasion
                try:
                    reason = "Ban evasion detected — linked to a banned account."
                    player.kick(f"§c{reason}")
                except Exception:
                    pass
                return  # Only need to find one banned link

    def get_fingerprint(self, uuid_str: str) -> dict:
        """Public API: Get fingerprint data for a player."""
        data = self.db.get("fingerprints", uuid_str, {})
        return data if isinstance(data, dict) else {}

    def get_all_fingerprints(self) -> dict:
        """Public API: Get all fingerprint records."""
        return self.db.get_all("fingerprints")

    # ── Trusted Links (Family / Household Exemptions) ─────

    @staticmethod
    def _make_pair_key(uuid_a: str, uuid_b: str) -> str:
        """Create a deterministic key for a pair of UUIDs."""
        return "|".join(sorted([uuid_a, uuid_b]))

    def is_trusted_pair(self, uuid_a: str, uuid_b: str) -> bool:
        """Check if two players are in a trusted pair."""
        key = self._make_pair_key(uuid_a, uuid_b)
        return self.db.has("trusted_links", key)

    def add_trusted_link(self, uuid_a: str, uuid_b: str, name_a: str = "", name_b: str = ""):
        """Add a trusted link between two players."""
        key = self._make_pair_key(uuid_a, uuid_b)
        self.db.set("trusted_links", key, {
            "uuid_a": uuid_a,
            "uuid_b": uuid_b,
            "name_a": name_a,
            "name_b": name_b,
            "created_at": time.time(),
        })

    def remove_trusted_link(self, uuid_a: str, uuid_b: str):
        """Remove a trusted link between two players."""
        key = self._make_pair_key(uuid_a, uuid_b)
        self.db.delete("trusted_links", key)

    def get_all_trusted_links(self) -> dict:
        """Public API: Get all trusted link records."""
        return self.db.get_all("trusted_links")

    # ── Global Intelligence Network Integration ──────────────

    def _push_to_global(self, fingerprint_hash: str, record: dict):
        """Push this fingerprint to the Global Intelligence Network."""
        api = getattr(self.plugin, '_global_api', None)
        if api is None or not hasattr(api, 'push_fingerprint'):
            return

        # Count local violations for this player
        uuid_str = record.get("uuid", "")
        violation_count = 0
        try:
            all_violations = self.db.get_all("violations")
            for key, data in all_violations.items():
                if isinstance(data, dict) and data.get("uuid") == uuid_str:
                    violation_count += 1
        except Exception:
            pass

        # Build linked fingerprint hashes
        linked_hashes = []
        for linked_uuid in record.get("linked_uuids", []):
            linked_fp = self.db.get("fingerprints", linked_uuid, {})
            if isinstance(linked_fp, dict) and linked_fp.get("fingerprint"):
                linked_hashes.append(linked_fp["fingerprint"])

        # Check if player is banned locally
        is_banned = (
            self.db.has("bans", uuid_str) or
            self.db.has("bans", record.get("name", "").lower())
        )

        try:
            api.push_fingerprint(
                fingerprint_hash=fingerprint_hash,
                linked_hashes=linked_hashes,
                violation_count=violation_count,
                is_banned=is_banned,
            )
        except Exception:
            pass

    def _check_global_intelligence(self, player, fingerprint_hash: str, record: dict):
        """Cross-check fingerprint against globally flagged fingerprints."""
        api = getattr(self.plugin, '_global_api', None)
        if api is None or not hasattr(api, 'get_flagged_fingerprints'):
            return

        # Check if this fingerprint is globally flagged
        try:
            flagged = api.get_flagged_fingerprints()
        except Exception:
            return

        if fingerprint_hash in flagged:
            self.alert_admins(
                f"§c⚠ GLOBAL FLAG: §c{player.name}§e has a fingerprint "
                f"flagged by the §cGlobal Intelligence Network§e!"
            )
            self.emit(player, severity=3, evidence={
                "type": "global_flag",
                "fingerprint": fingerprint_hash[:8],
                "desc": "Fingerprint flagged by multiple Paradox servers",
            })

        # Also check linked fingerprints
        for linked_uuid in record.get("linked_uuids", []):
            linked_fp = self.db.get("fingerprints", linked_uuid, {})
            if isinstance(linked_fp, dict):
                linked_hash = linked_fp.get("fingerprint", "")
                if linked_hash and linked_hash in flagged:
                    self.alert_admins(
                        f"§e🔍 {player.name}§e is linked to a §cglobally flagged§e account"
                    )
                    break

        # Check global reputation score
        try:
            rep_score = api.get_global_reputation(fingerprint_hash)
            if rep_score < 30:
                self.alert_admins(
                    f"§c⚠ {player.name}§e has a low global reputation: "
                    f"§c{rep_score}/100§e — known across multiple servers"
                )
                self.emit(player, severity=2, evidence={
                    "type": "low_reputation",
                    "reputation": rep_score,
                    "fingerprint": fingerprint_hash[:8],
                    "desc": f"Global reputation score: {rep_score}/100",
                })
        except Exception:
            pass
