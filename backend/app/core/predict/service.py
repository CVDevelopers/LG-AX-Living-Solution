"""Top-level pure prediction service — assembles the §6 /api/predict payload.

Pure module: inputs are plain types (§1.1), output is a JSON-ready dict. The API layer only
converts DB rows to core types and hands over the request parameters. Deterministic for a
given input and seed, which is what the golden-file tests pin down (§8.3).
"""

import numpy as np

from ... import config
from .bootstrap import summarize_mode, t_est_minutes, t_req_minutes
from .engine import RuleEngineV1
from .state import decide_state
from .types import Segment, SessionStat, Zone


def _round(x: float, nd: int = 2) -> float:
    return float(round(x, nd))


def predict(
    battery_pct: float,
    mode: str,
    zones: list[Zone],
    segments: list[Segment],
    session_stats: list[SessionStat],
    prev_state: str | None = None,
    seed: int = config.PREDICT_SEED,
) -> dict:
    engine = RuleEngineV1(segments, session_stats)
    rng = np.random.default_rng(seed)
    draws = engine.joint_draws(rng)

    summaries = {m: summarize_mode(battery_pct, zones, draws, m) for m in config.MODES}
    fit = engine.fit

    per_mode = {}
    for m in config.MODES:
        t_est_m = t_est_minutes(battery_pct, fit.r_tilde[m])
        per_mode[m] = {
            "t_est_min": _round(float(t_est_m)),
            "p_complete": _round(summaries[m]["p_complete"], 3),
        }

    p_cur = summaries[mode]["p_complete"]
    p_by_mode = {m: summaries[m]["p_complete"] for m in config.MODES}
    state, recommended = decide_state(p_cur, p_by_mode, fit.n_eff, battery_pct, prev_state)

    t_req_point = t_req_minutes(
        zones, engine.speed[mode], config.TREQ_CARPET_COEF, config.TREQ_DIRT_COEF
    )
    # Charge suggestion for the shortage banner (§4.2): reach enough SoC for a full clean.
    needed_pct = config.B_RES_DEFAULT_PCT + float(t_req_point) * fit.r_tilde[mode] * 1.1
    charge_min = max(0.0, (min(needed_pct, 100.0) - battery_pct) / config.CHARGE_RATE_PCT_MIN)

    cur = summaries[mode]
    return {
        "engine": engine.name,
        "mode": mode,
        "battery_pct": _round(battery_pct, 1),
        "t_est_min": per_mode[mode]["t_est_min"],
        "t_lo_min": _round(cur["t_lo_min"]),
        "t_hi_min": _round(cur["t_hi_min"]),
        "t_req_min": _round(float(t_req_point)),
        "t_req_lo": _round(cur["t_req_lo"]),
        "t_req_hi": _round(cur["t_req_hi"]),
        "p_complete": _round(p_cur, 3),
        "state": state,
        "recommended_mode": recommended,
        "charge_min": _round(charge_min, 0),
        "per_mode": per_mode,
        "basis": {
            "n_eff": _round(fit.n_eff, 1),
            "segments_used": fit.segments_used,
            "ewma_halflife": int(config.HALFLIFE_DRIFT_SESSIONS),
            "base_rate": _round(fit.base[mode], 3),
            "drift": _round(fit.drift, 3),
            "prior_weight": _round(fit.prior_weight(mode), 2),
            "interval_method": "joint_weighted_bootstrap",
            "B": config.BOOTSTRAP_B,
            "low_data": bool(fit.n_eff < config.N_EFF_LOW),
        },
    }
