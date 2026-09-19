# player_baseline.py - Per-player rolling averages via Exponential Moving Average
# Detects behavioral deviation (z-score) rather than relying on fixed thresholds.

import math
import time
from collections import defaultdict
from typing import Optional, NamedTuple


class DeviationResult(NamedTuple):
    """Result of recording a metric sample."""
    is_deviation: bool    # True if value deviates from baseline
    z_score: float        # How many std devs from the mean
    avg: float            # Player's rolling average
    std: float            # Player's rolling std dev
    value: float          # The recorded value
    warming_up: bool      # True if still in warmup (not enough samples)


class _MetricState:
    """EMA state for a single metric."""
    __slots__ = ("avg", "var", "count")

    def __init__(self, avg: float = 0.0, var: float = 0.0, count: int = 0):
        self.avg = avg
        self.var = var
        self.count = count

    def to_dict(self) -> dict:
        return {"avg": self.avg, "var": self.var, "count": self.count}

    @staticmethod
    def from_dict(d: dict) -> "_MetricState":
        return _MetricState(
            avg=d.get("avg", 0.0),
            var=d.get("var", 0.0),
            count=d.get("count", 0),
        )


class PlayerBaseline:
    """Per-player behavioral baseline tracker using Exponential Moving Averages.

    Usage:
        result = baseline.record(uuid, "combat.hit_distance", 3.2)
        if result.is_deviation:
            # Player's hit distance is abnormally high compared to THEIR baseline

    Config:
        alpha:       EMA smoothing factor (0.0-1.0). Lower = smoother, slower adapt.
        z_threshold: Z-score threshold to flag deviation (default 2.5).
        warmup:      Minimum samples before deviations are flagged (default 30).
    """

    def __init__(self, db, logger, alpha: float = 0.1,
                 z_threshold: float = 3.0, warmup: int = 60):
        self._db = db
        self._logger = logger
        self._alpha = alpha
        self._z_threshold = z_threshold
        self._warmup = warmup

        # uuid -> { metric_key -> _MetricState }
        self._profiles: dict[str, dict[str, _MetricState]] = defaultdict(dict)

        # Track which profiles are dirty (need DB flush)
        self._dirty: set = set()

    # ── Primary API ──────────────────────────────────────────

    def record(self, uuid_str: str, metric: str, value: float) -> DeviationResult:
        """Record a metric sample and check for deviation.

        Args:
            uuid_str: Player UUID string
            metric:   Metric key (e.g. "combat.hit_distance")
            value:    The observed value

        Returns:
            DeviationResult with deviation status and statistics.
        """
        profile = self._profiles[uuid_str]
        state = profile.get(metric)

        if state is None:
            # First sample — initialize
            state = _MetricState(avg=value, var=0.0, count=1)
            profile[metric] = state
            self._dirty.add(uuid_str)
            return DeviationResult(
                is_deviation=False, z_score=0.0,
                avg=value, std=0.0, value=value, warming_up=True
            )

        # Update count
        state.count += 1

        # EMA update
        alpha = self._alpha
        delta = value - state.avg
        state.avg += alpha * delta
        # EMA of variance: var = (1-alpha) * (var + alpha * delta^2)
        state.var = (1.0 - alpha) * (state.var + alpha * delta * delta)

        std = math.sqrt(max(state.var, 0.0))

        # Calculate z-score
        if std > 1e-9:
            z_score = abs(delta) / std
        else:
            z_score = 0.0

        warming_up = state.count < self._warmup
        is_deviation = (not warming_up) and (z_score > self._z_threshold)

        self._dirty.add(uuid_str)

        return DeviationResult(
            is_deviation=is_deviation,
            z_score=round(z_score, 2),
            avg=round(state.avg, 4),
            std=round(std, 4),
            value=value,
            warming_up=warming_up,
        )

    def get_profile(self, uuid_str: str) -> dict:
        """Get all metric states for a player (for inspection/web UI)."""
        profile = self._profiles.get(uuid_str, {})
        return {k: v.to_dict() for k, v in profile.items()}

    def get_metric(self, uuid_str: str, metric: str) -> Optional[_MetricState]:
        """Get a single metric state."""
        return self._profiles.get(uuid_str, {}).get(metric)

    # ── Lifecycle ────────────────────────────────────────────

    def load(self, uuid_str: str):
        """Load a player's baseline from DB."""
        stored = self._db.get("baselines", uuid_str)
        if stored and isinstance(stored, dict):
            profile = {}
            for key, data in stored.items():
                if isinstance(data, dict):
                    profile[key] = _MetricState.from_dict(data)
            self._profiles[uuid_str] = profile

    def flush(self, uuid_str: str = None):
        """Persist dirty profiles to DB.

        Args:
            uuid_str: Flush a specific player (or all dirty if None).
        """
        if uuid_str:
            if uuid_str in self._dirty:
                self._write(uuid_str)
                self._dirty.discard(uuid_str)
        else:
            for uid in list(self._dirty):
                self._write(uid)
            self._dirty.clear()

    def on_player_leave(self, uuid_str: str):
        """Flush and release memory for a leaving player."""
        self.flush(uuid_str)
        self._profiles.pop(uuid_str, None)

    # ── Internal ─────────────────────────────────────────────

    def _write(self, uuid_str: str):
        """Serialize and persist a player's profile."""
        profile = self._profiles.get(uuid_str)
        if not profile:
            return
        data = {k: v.to_dict() for k, v in profile.items()}
        try:
            self._db.set("baselines", uuid_str, data)
        except Exception as e:
            self._logger.warning(
                f"§2[§7Paradox§2]§e Baseline flush failed for {uuid_str[:8]}: {e}"
            )
