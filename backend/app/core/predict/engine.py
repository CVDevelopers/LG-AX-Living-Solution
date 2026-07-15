"""Engine contract (SPEC §3.7).

Every engine — v1 rule, v2 RLS (M4), v3 LSTM (M4) — supplies the same two primitives, so the
state decision, heatmap rollout and planner never know which engine produced the distribution.
"""

from typing import Protocol

import numpy as np

from ... import config
from .bootstrap import draw_joint
from .estimator import fit_estimator, fit_speed
from .types import Segment, SessionStat


class RateEngine(Protocol):
    name: str

    def sample_rates(self, mode: str, n: int, rng: np.random.Generator) -> np.ndarray: ...

    def quantiles(self, mode: str) -> tuple[float, float, float]: ...


class RuleEngineV1:
    """v1 — the default engine: shrunk base × shared drift + joint weighted bootstrap (§3.2)."""

    name = "rule_v1"

    def __init__(self, segments: list[Segment], session_stats: list[SessionStat]):
        self.segments = segments
        self.session_stats = session_stats
        self.fit = fit_estimator(segments)
        self.speed = fit_speed(session_stats)

    def joint_draws(self, rng: np.random.Generator, b: int = config.BOOTSTRAP_B):
        return draw_joint(self.segments, self.session_stats, rng, b)

    def sample_rates(self, mode: str, n: int, rng: np.random.Generator) -> np.ndarray:
        return self.joint_draws(rng, b=n).rates[mode]

    def quantiles(self, mode: str) -> tuple[float, float, float]:
        rng = np.random.default_rng(config.PREDICT_SEED)
        r = self.sample_rates(mode, config.BOOTSTRAP_B, rng)
        return tuple(float(np.percentile(r, q)) for q in (5, 50, 95))
