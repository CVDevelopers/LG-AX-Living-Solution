"""Joint weighted bootstrap (SPEC §3.2–3.3).

T_est and T_req share the same discharge-rate uncertainty, so both are computed inside the
same draw: resample segments with P ∝ w_j, refit base*/drift* on the resample, resample
session speeds ṽ*, draw shared coefficient noise — then T*_b and T_req*_b per mode.
The completion probability P = #{T*_b ≥ T_req*_b}/B and the interval [p5, p95] therefore
can never contradict each other or the state decision (§1 principle 7).

Predictive layer: each draw additionally samples ONE historical session (recency-weighted) —
its standardized consumption residual ρ_b scales the rate draw, and its observed coverage
speed feeds T_req when it ran the requested mode. One realized session drives both sides of
a draw, so T*_b and T_req*_b are correlated the way real sessions are (§8.3 tests this),
and the interval is a *predictive* interval — what the §8.1 coverage gate (86–94 %) checks.
Estimated from logs only; no simulator constants (§1 principle 3).
"""

from dataclasses import dataclass

import numpy as np

from ... import config
from .estimator import fit_estimator, segment_weights, session_speed
from .types import Segment, SessionStat, Zone

COLD_START_REL_SIGMA = 0.15  # rate spread when no segments exist yet  [modeling choice]


@dataclass
class JointDraws:
    """Per-mode arrays of B joint draws."""

    rates: dict[str, np.ndarray]  # r̃*_s  (%/min)
    speeds: dict[str, np.ndarray]  # ṽ*_s  (m²/min, hardfloor-equivalent)
    carpet_coef: np.ndarray  # shared T_req coefficient noise per draw
    dirt_coef: np.ndarray


def draw_joint(
    segments: list[Segment],
    session_stats: list[SessionStat],
    rng: np.random.Generator,
    b: int = config.BOOTSTRAP_B,
) -> JointDraws:
    prior = config.R_PRIOR_PCT_MIN
    k = config.SHRINK_K
    mode_index = {m: i for i, m in enumerate(config.MODES)}
    fit = fit_estimator(segments)

    # ── Estimator uncertainty: weighted bootstrap over segments → base*, drift* ─────────
    if segments:
        n = len(segments)
        w = segment_weights(segments)
        p = w / w.sum()
        rate = np.array([s.rate for s in segments])
        midx = np.array([mode_index[s.mode] for s in segments])

        idx = rng.choice(n, size=(b, n), p=p)  # weighted bootstrap resample
        rates_mat = rate[idx]
        modes_mat = midx[idx]

        base_star = np.empty((b, len(config.MODES)))
        for i, m in enumerate(config.MODES):
            mask = modes_mat == i
            cnt = mask.sum(axis=1)
            mean_s = np.where(cnt > 0, (rates_mat * mask).sum(axis=1) / np.maximum(cnt, 1), 0.0)
            base_star[:, i] = (cnt * mean_s + k * prior[m]) / (cnt + k)

        base_per_item = np.take_along_axis(base_star, modes_mat, axis=1)
        drift_star = (rates_mat / base_per_item).mean(axis=1)
        est_rates = {m: base_star[:, i] * drift_star for i, m in enumerate(config.MODES)}
    else:
        # Cold start: prior-centered draws so the interval reflects prior uncertainty (§3.2).
        est_rates = {
            m: np.maximum(rng.normal(prior[m], COLD_START_REL_SIGMA * prior[m], size=b), 1e-3)
            for m in config.MODES
        }

    # ── Predictive session layer: one clean historical session per draw ─────────────────
    clean = [
        s
        for s in session_stats
        if s.mode_changes == 0 and s.duration_min > 0 and s.cleaned_area_m2 > 0 and s.dsoc > 0
    ]
    per_mode_pool: dict[str, list[int]] = {
        m: [i for i, s in enumerate(clean) if s.mode == m] for m in config.MODES
    }

    if clean:
        w_c = np.array([config.LAMBDA_AGE**s.age for s in clean])
        v_all = np.array([session_speed(s) for s in clean])
        r_point = {m: fit.base[m] * fit.drift for m in config.MODES}
        rho_all = np.array([(s.dsoc / s.duration_min) / r_point[s.mode] for s in clean])

        pick = rng.choice(len(clean), size=b, p=w_c / w_c.sum())
        rho = rho_all[pick]
        pick_mode = np.array([mode_index[clean[i].mode] for i in pick])
    else:
        v_all = None
        rho = np.ones(b)
        pick = pick_mode = None

    rates = {m: est_rates[m] * rho for m in config.MODES}

    speeds: dict[str, np.ndarray] = {}
    for i, m in enumerate(config.MODES):
        pool = per_mode_pool[m]
        if not pool:
            speeds[m] = np.full(b, config.V_COVER_M2_MIN[m])
            continue
        w_m = np.array([config.LAMBDA_AGE ** clean[j].age for j in pool])
        fallback = np.array(pool)[rng.choice(len(pool), size=b, p=w_m / w_m.sum())]
        # Use the draw's own session when it ran this mode; else a weighted same-mode pick.
        chosen = np.where(pick_mode == i, pick, fallback)
        speeds[m] = v_all[chosen]

    return JointDraws(
        rates=rates,
        speeds=speeds,
        carpet_coef=rng.normal(config.TREQ_CARPET_COEF, config.TREQ_CARPET_COEF_SIGMA, size=b),
        dirt_coef=rng.normal(config.TREQ_DIRT_COEF, config.TREQ_DIRT_COEF_SIGMA, size=b),
    )


def travel_minutes(zones: list[Zone]) -> float:
    """v0 transit estimate; the real visit-order path arrives with the M1 planner (§3.3)."""
    return len(zones) * config.TRAVEL_M_PER_ZONE / config.V_TRAVEL_M_MIN


def t_req_minutes(zones: list[Zone], speed, carpet_coef, dirt_coef):
    """§3.3 — accepts scalars (point estimate) or per-draw arrays (bootstrap)."""
    total = 0.0
    for z in zones:
        total = total + (z.area_m2 / speed) * (1 + carpet_coef * z.carpet_ratio) * (
            1 + dirt_coef * z.avg_dirt
        )
    return total + travel_minutes(zones)


def t_est_minutes(battery_pct: float, rate, b_res: float = config.B_RES_DEFAULT_PCT):
    return np.maximum(battery_pct - b_res, 0.0) / rate


def summarize_mode(
    battery_pct: float,
    zones: list[Zone],
    draws: JointDraws,
    mode: str,
    b_res: float = config.B_RES_DEFAULT_PCT,
) -> dict[str, float]:
    """Interval, T_req interval and completion probability for one mode from the joint draws."""
    t_star = t_est_minutes(battery_pct, draws.rates[mode], b_res)
    t_req_star = t_req_minutes(zones, draws.speeds[mode], draws.carpet_coef, draws.dirt_coef)
    return {
        "t_lo_min": float(np.percentile(t_star, config.INTERVAL_LO_PCT)),
        "t_hi_min": float(np.percentile(t_star, config.INTERVAL_HI_PCT)),
        "t_req_lo": float(np.percentile(t_req_star, config.INTERVAL_LO_PCT)),
        "t_req_hi": float(np.percentile(t_req_star, config.INTERVAL_HI_PCT)),
        "p_complete": float((t_star >= t_req_star).mean()),
    }
