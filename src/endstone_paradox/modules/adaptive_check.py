# adaptive_check.py - Adaptive Check Frequency (Tier 3)
# Dynamically adjusts how often detection modules check each player
# based on their violation history. Clean players → less often, flagged → every tick.

import time
from collections import defaultdict
from endstone_paradox.modules.base import BaseModule


# Risk tiers and their check-interval multipliers
TIER_LOW = "low"
TIER_MEDIUM = "medium"
TIER_HIGH = "high"

# Score thresholds (from violation engine rolling score)
LOW_THRESHOLD = 2.0      # below this → low risk
HIGH_THRESHOLD = 8.0     # above this → high risk

# Check interval multipliers (applied to each module's base interval)
INTERVAL_MULTIPLIERS = {
    TIER_LOW: 2.0,       # 2x normal interval (less frequent)
    TIER_MEDIUM: 1.0,    # normal
    TIER_HIGH: 0.5,      # half interval (more frequent)
}


class AdaptiveCheckModule(BaseModule):
    """Adjusts detection module check frequencies based on per-player risk tiers.

    Clean players are checked less often to save server resources,
    while flagged players are checked more frequently for faster detection.
    """

    @property
    def name(self) -> str:
        return "adaptivecheck"

    @property
    def check_interval(self) -> int:
        # Re-evaluate tiers every 10 seconds
        return 200

    def on_start(self):
        self._player_tiers = {}          # uuid -> current tier
        self._tier_change_times = {}     # uuid -> last tier change timestamp
        self._original_intervals = {}    # module_name -> original check_interval
        self._snapshot_intervals()

    def on_stop(self):
        # Restore original intervals
        self._restore_intervals()
        self._player_tiers.clear()
        self._tier_change_times.clear()

    def _snapshot_intervals(self):
        """Record the original check_interval for every detection module."""
        for mod_name, module in self.plugin._modules.items():
            if mod_name != self.name and hasattr(module, 'check_interval'):
                self._original_intervals[mod_name] = module.check_interval

    def _restore_intervals(self):
        """Reset all modules back to their original check intervals."""
        for mod_name, original in self._original_intervals.items():
            module = self.plugin._modules.get(mod_name)
            if module and hasattr(module, '_adaptive_interval'):
                del module._adaptive_interval

    def check(self):
        """Periodic re-evaluation of all online player risk tiers."""
        engine = getattr(self.plugin, 'violation_engine', None)
        if engine is None:
            return

        now = time.time()
        online = self.plugin.server.online_players

        # Track which tiers are active for interval adjustment
        has_high = False
        has_medium = False

        for player in online:
            uuid_str = str(player.unique_id)

            # Calculate current violation score
            score = engine._calc_score(uuid_str, now)

            # Determine tier
            if score >= self._scale(HIGH_THRESHOLD):
                new_tier = TIER_HIGH
                has_high = True
            elif score >= self._scale(LOW_THRESHOLD):
                new_tier = TIER_MEDIUM
                has_medium = True
            else:
                new_tier = TIER_LOW

            old_tier = self._player_tiers.get(uuid_str)

            if old_tier != new_tier:
                self._player_tiers[uuid_str] = new_tier
                self._tier_change_times[uuid_str] = now

                # Alert on escalation
                if old_tier is not None and self._tier_rank(new_tier) > self._tier_rank(old_tier):
                    self.alert_admins(
                        f"§c{player.name}§e risk tier escalated: "
                        f"§7{old_tier}§e → §c{new_tier}§e "
                        f"(score: {score:.1f})"
                    )

        # Adjust module intervals based on highest active tier
        if has_high:
            self._apply_global_multiplier(INTERVAL_MULTIPLIERS[TIER_HIGH])
        elif has_medium:
            self._apply_global_multiplier(INTERVAL_MULTIPLIERS[TIER_MEDIUM])
        else:
            self._apply_global_multiplier(INTERVAL_MULTIPLIERS[TIER_LOW])

    def _apply_global_multiplier(self, multiplier: float):
        """Apply an interval multiplier to all detection modules."""
        for mod_name, original in self._original_intervals.items():
            module = self.plugin._modules.get(mod_name)
            if module and module.running:
                new_interval = max(5, int(original * multiplier))
                module._adaptive_interval = new_interval

    @staticmethod
    def _tier_rank(tier: str) -> int:
        return {TIER_LOW: 0, TIER_MEDIUM: 1, TIER_HIGH: 2}.get(tier, 0)

    def on_player_join(self, player):
        uuid_str = str(player.unique_id)
        self._player_tiers[uuid_str] = TIER_MEDIUM  # start at medium

    def on_player_leave(self, player):
        uuid_str = str(player.unique_id)
        self._player_tiers.pop(uuid_str, None)
        self._tier_change_times.pop(uuid_str, None)

    def get_player_tier(self, player) -> str:
        """Public API: get current risk tier for a player."""
        uuid_str = str(player.unique_id)
        return self._player_tiers.get(uuid_str, TIER_LOW)

    def get_tier_summary(self) -> dict:
        """Return counts per tier (for web UI / dashboard)."""
        counts = {TIER_LOW: 0, TIER_MEDIUM: 0, TIER_HIGH: 0}
        for tier in self._player_tiers.values():
            counts[tier] = counts.get(tier, 0) + 1
        return counts

    # ── Global Intelligence Network Integration ──────────────

    def _push_tier_telemetry(self):
        """Push tier distribution telemetry to the Global Intelligence Network."""
        api = getattr(self.plugin, '_global_api', None)
        if api is None or not hasattr(api, 'push_telemetry_event'):
            return

        summary = self.get_tier_summary()
        total = sum(summary.values())
        if total == 0:
            return

        try:
            # Push proportion of high-risk players as a telemetry metric
            high_ratio = summary.get(TIER_HIGH, 0) / total
            api.push_telemetry_event(
                module=self.name,
                metric="high_risk_ratio",
                value=round(high_ratio, 3),
                sample_size=total,
            )

            # Push tier counts
            for tier, count in summary.items():
                api.push_telemetry_event(
                    module=self.name,
                    metric=f"tier_{tier}_count",
                    value=count,
                    sample_size=1,
                )
        except Exception:
            pass

    def apply_global_thresholds(self):
        """Check for and optionally apply crowd-sourced threshold recommendations."""
        api = getattr(self.plugin, '_global_api', None)
        if api is None or not hasattr(api, 'get_recommended_thresholds'):
            return

        try:
            thresholds = api.get_recommended_thresholds()
            if not thresholds or not isinstance(thresholds, dict):
                return

            # Log what the network recommends (for admin awareness)
            for module_name, suggested in thresholds.items():
                module = self.plugin._modules.get(module_name)
                if module and hasattr(module, 'sensitivity'):
                    current = module.sensitivity
                    if current != int(suggested):
                        self.alert_admins(
                            f"§7[Intelligence] §e{module_name}§7: "
                            f"network suggests sensitivity §f{int(suggested)}§7 "
                            f"(current: §f{current}§7)"
                        )
        except Exception:
            pass
