# report_system.py - Player Report System (Tier 3)
# /ac-report command, web UI queue, auto-escalation, staff claim/resolve workflow.

import time
import uuid as uuid_mod
from endstone_paradox.modules.base import BaseModule


# Report statuses
STATUS_OPEN = "open"
STATUS_PRIORITY = "priority"
STATUS_CLAIMED = "claimed"
STATUS_RESOLVED = "resolved"

# Auto-escalation: open reports older than this become priority
ESCALATION_THRESHOLD = 300.0   # 5 minutes

# Rate limit: max 1 report per player per this many seconds
REPORT_COOLDOWN = 60.0


class ReportSystemModule(BaseModule):
    """Player report system with queue management and auto-escalation.

    Features:
    - Any player can submit reports via /ac-report
    - Reports queue in the DB with status tracking
    - Auto-escalation promotes old reports to priority
    - Staff can claim and resolve reports via web UI
    - Rate-limited to prevent spam
    """

    @property
    def name(self) -> str:
        return "reportsystem"

    @property
    def check_interval(self) -> int:
        # Check for auto-escalation every 30 seconds
        return 600

    def on_start(self):
        self._cooldowns = {}   # uuid -> last report timestamp
        self.db._ensure_table("reports")

    def on_stop(self):
        self._cooldowns.clear()

    # ── Public API ───────────────────────────────────────────

    def submit_report(self, reporter, target_name: str, reason: str) -> dict:
        """Submit a new player report.

        Args:
            reporter: Player object of the reporter
            target_name: Name of the reported player
            reason: Free-text reason for the report

        Returns:
            dict with report data, or None if rate-limited.
        """
        reporter_uuid = str(reporter.unique_id)
        now = time.time()

        # Rate limit check
        last = self._cooldowns.get(reporter_uuid, 0)
        if now - last < self._scale(REPORT_COOLDOWN):
            remaining = int(REPORT_COOLDOWN - (now - last))
            return {"error": f"Please wait {remaining}s before reporting again."}

        self._cooldowns[reporter_uuid] = now

        report_id = str(uuid_mod.uuid4())[:8]
        report_data = {
            "id": report_id,
            "reporter": reporter.name,
            "reporter_uuid": reporter_uuid,
            "target": target_name,
            "reason": reason or "No reason given",
            "status": STATUS_OPEN,
            "created_at": now,
            "claimed_by": None,
            "resolved_at": None,
            "resolution": None,
        }

        self.db.set("reports", report_id, report_data)

        # Alert staff
        self.alert_admins(
            f"§e📋 New report: §c{target_name}§e reported by "
            f"§7{reporter.name}§e — §f{reason or 'No reason'}"
        )

        return report_data

    def get_reports(self, status: str = None) -> list:
        """Get all reports, optionally filtered by status."""
        all_reports = self.db.get_all("reports")
        reports = []
        for key, data in all_reports.items():
            if not isinstance(data, dict):
                continue
            if status is None or data.get("status") == status:
                reports.append(data)
        # Sort by priority first, then creation time
        reports.sort(key=lambda r: (
            0 if r.get("status") == STATUS_PRIORITY else 1,
            r.get("created_at", 0),
        ))
        return reports

    def get_open_count(self) -> int:
        """Return count of open + priority reports."""
        reports = self.get_reports()
        return sum(1 for r in reports if r.get("status") in (STATUS_OPEN, STATUS_PRIORITY))

    def claim_report(self, report_id: str, staff_name: str) -> bool:
        """Staff claims a report for investigation."""
        report = self.db.get("reports", report_id)
        if report is None or not isinstance(report, dict):
            return False
        if report.get("status") not in (STATUS_OPEN, STATUS_PRIORITY):
            return False

        report["status"] = STATUS_CLAIMED
        report["claimed_by"] = staff_name
        self.db.set("reports", report_id, report)
        return True

    def resolve_report(self, report_id: str, resolution: str) -> bool:
        """Resolve a claimed report."""
        report = self.db.get("reports", report_id)
        if report is None or not isinstance(report, dict):
            return False
        if report.get("status") not in (STATUS_OPEN, STATUS_PRIORITY, STATUS_CLAIMED):
            return False

        report["status"] = STATUS_RESOLVED
        report["resolved_at"] = time.time()
        report["resolution"] = resolution
        self.db.set("reports", report_id, report)
        return True

    # ── Periodic check ───────────────────────────────────────

    def check(self):
        """Auto-escalate old open reports to priority status."""
        now = time.time()
        threshold = self._scale(ESCALATION_THRESHOLD)
        all_reports = self.db.get_all("reports")

        escalated = 0
        for key, data in all_reports.items():
            if not isinstance(data, dict):
                continue
            if data.get("status") != STATUS_OPEN:
                continue
            age = now - data.get("created_at", now)
            if age >= threshold:
                data["status"] = STATUS_PRIORITY
                self.db.set("reports", key, data)
                escalated += 1

        if escalated > 0:
            self.alert_admins(
                f"§e⚠ {escalated} report(s) auto-escalated to §cpriority§e "
                f"(unresolved > {int(threshold)}s)"
            )

    # ── Player events ────────────────────────────────────────

    def on_player_leave(self, player):
        uuid_str = str(player.unique_id)
        self._cooldowns.pop(uuid_str, None)
