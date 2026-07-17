"""Hierarchical shrinkage × shared drift estimator (SPEC §3.2).

Two time scales: per-mode base rates move slowly (half-life 40 sessions, shrunk toward the
prior with pseudo-count k), while a single drift factor shared by every stratum moves fast
(half-life 10) so aging observed in any mode propagates to sparse modes immediately.
No cold-start branch: with no data the base converges to the prior and drift to 1.
"""

from dataclasses import dataclass, field

import numpy as np

from ... import config
from .types import Segment, SessionStat


def _age_weight(age: np.ndarray, halflife: float) -> np.ndarray:
    return 0.5 ** (age / halflife)


def _length_weight(dt: np.ndarray) -> np.ndarray:
    return dt / config.SEG_LEN_NORM_MIN


def segment_weights(segments: list[Segment]) -> np.ndarray:
    """§3.1 sample weights: w_j = λ^age × (Δt/10), λ = 0.933 ≡ half-life 10 sessions."""
    age = np.array([s.age for s in segments], dtype=float)
    dt = np.array([s.dt_min for s in segments], dtype=float)
    return (config.LAMBDA_AGE**age) * _length_weight(dt)


def kish_n_eff(weights: np.ndarray) -> float:
    if weights.size == 0 or float(weights.sum()) == 0.0:
        return 0.0
    return float(weights.sum() ** 2 / (weights**2).sum())


@dataclass
class EstimatorFit:
    base: dict[str, float]
    drift: float
    r_tilde: dict[str, float] = field(default_factory=dict)
    n_eff: float = 0.0  # overall, §3.1 weights (Kish)
    n_eff_by_mode: dict[str, float] = field(default_factory=dict)  # per-stratum, half-life 40
    segments_used: int = 0

    def prior_weight(self, mode: str) -> float:
        return config.SHRINK_K / (self.n_eff_by_mode.get(mode, 0.0) + config.SHRINK_K)


def fit_estimator(segments: list[Segment]) -> EstimatorFit:
    prior = config.R_PRIOR_PCT_MIN
    if not segments:
        return EstimatorFit(
            base=dict(prior),
            drift=1.0,
            r_tilde=dict(prior),
            n_eff_by_mode={m: 0.0 for m in config.MODES},
        )

    age = np.array([s.age for s in segments], dtype=float)
    dt = np.array([s.dt_min for s in segments], dtype=float)
    rate = np.array([s.rate for s in segments], dtype=float)
    mode = np.array([s.mode for s in segments])

    base: dict[str, float] = {}
    n_eff_by_mode: dict[str, float] = {}
    for m in config.MODES:
        sel = mode == m
        w40 = _age_weight(age[sel], config.HALFLIFE_BASE_SESSIONS) * _length_weight(dt[sel])
        n_eff_s = kish_n_eff(w40)
        r_hat = float((w40 * rate[sel]).sum() / w40.sum()) if n_eff_s > 0 else prior[m]
        base[m] = (n_eff_s * r_hat + config.SHRINK_K * prior[m]) / (n_eff_s + config.SHRINK_K)
        n_eff_by_mode[m] = n_eff_s

    w10 = segment_weights(segments)
    base_per_seg = np.array([base[m] for m in mode])
    drift = float((w10 * (rate / base_per_seg)).sum() / w10.sum())

    return EstimatorFit(
        base=base,
        drift=drift,
        r_tilde={m: base[m] * drift for m in config.MODES},
        n_eff=kish_n_eff(w10),
        n_eff_by_mode=n_eff_by_mode,
        segments_used=len(segments),
    )


def session_speed(s: SessionStat) -> float:
    """Invert §3.3 at session granularity to a normalized coverage speed.

    ṽ ≈ area × (1 + 0.6·carpet) × (1 + 0.003·dirt̄) / duration. Per-session zone dirt is not
    in the v0 logs, so the inversion is standardized at the default zone dirt (DIRT_MEAN) —
    exactly what the forward T_req multiplies back in, so the two cancel at default dirt.
    """
    dirt_std = 1 + config.TREQ_DIRT_COEF * config.DIRT_MEAN
    carpet = 1 + config.TREQ_CARPET_COEF * s.carpet_ratio
    return s.cleaned_area_m2 * carpet * dirt_std / s.duration_min


def fit_speed(session_stats: list[SessionStat]) -> dict[str, float]:
    """Normalized coverage speed ṽ per mode (§3.3), estimated from session logs.

    Sessions with mid-run mode changes are excluded (speed not attributable to one mode).
    Falls back to the reference prior V_COVER_M2_MIN when a stratum has no usable sessions.
    """
    v_hat = dict(config.V_COVER_M2_MIN)
    for m in config.MODES:
        usable = [
            s
            for s in session_stats
            if s.mode == m
            and s.mode_changes == 0
            and not s.charged  # exclude charge-resume sessions (§3.1)
            and s.duration_min > 0
            and s.cleaned_area_m2 > 0
        ]
        if not usable:
            continue
        w = np.array([config.LAMBDA_AGE**s.age for s in usable])
        v = np.array([session_speed(s) for s in usable])
        v_hat[m] = float((w * v).sum() / w.sum())
    return v_hat
