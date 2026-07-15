"""Zone-subset planner (SPEC §5.1) and trajectory rollout (§5.2) — two views of one dist.

Both read the SAME ``JointDraws`` the banner/interval/state read, so "one distribution, one
currency" (§1 principle 7) holds by construction: a subset the banner calls insufficient can
never be reported completable by the plan, and the heatmap's whole-plan completion probability
equals ``/api/predict``'s ``p_complete`` up to per-draw boundary flips.

Rollout identity (why the consistency test passes): the per-draw time to finish the last zone
is Σ_z (area_z/ṽ*)(1+carpet_coef*·carpet_z)(1+dirt_coef*·dirt_z) + K·travel — exactly the
§3.3 T_req* used by ``summarize_mode``. So P(finish all zones) ≡ P(T*_est ≥ T_req*).
"""

from dataclasses import dataclass
from itertools import combinations

import numpy as np

from ... import config
from .bootstrap import JointDraws, t_est_minutes, t_req_minutes
from .types import Zone

_TRAVEL_MIN_PER_ZONE = config.TRAVEL_M_PER_ZONE / config.V_TRAVEL_M_MIN


def subset_value(zones: list[Zone]) -> float:
    """§5.1 value v = Σ area_z × (1 + dirt_z/100) — finish the most (dirt-weighted) area."""
    return float(sum(z.area_m2 * (1.0 + z.avg_dirt / 100.0) for z in zones))


def completion_prob(
    battery_pct: float,
    zones: list[Zone],
    draws: JointDraws,
    mode: str,
    b_res: float = config.B_RES_DEFAULT_PCT,
) -> float:
    """P_S(mode) for cleaning ``zones`` — same joint draws as the banner (§3.2)."""
    t_star = t_est_minutes(battery_pct, draws.rates[mode], b_res)
    t_req_star = t_req_minutes(zones, draws.speeds[mode], draws.carpet_coef, draws.dirt_coef)
    return float((t_star >= t_req_star).mean())


@dataclass
class PlanResult:
    zones: list[Zone]  # chosen subset (input order; visit order is assigned downstream)
    mode: str
    p_complete: float  # P_S(mode)
    t_req_min: float  # median required minutes for the subset
    value: float  # Σ area × (1 + dirt/100)
    remaining_pct: float  # median battery left after the subset


def best_subset(
    battery_pct: float,
    zones: list[Zone],
    draws: JointDraws,
    b_res: float = config.B_RES_DEFAULT_PCT,
    threshold: float = config.P_SUFFICIENT,
) -> PlanResult | None:
    """§5.1 — argmax value over 2ⁿ−1 subsets × 3 modes s.t. P_S(mode) ≥ threshold.

    Value depends only on the subset, so ties (same subset, different feasible mode) break to
    the higher P_S (safer margin). Returns None when no subset completes in any mode → 부족B.
    """
    n = len(zones)
    best: PlanResult | None = None
    for r in range(1, n + 1):
        for combo in combinations(range(n), r):
            subset = [zones[i] for i in combo]
            value = subset_value(subset)
            if best is not None and value < best.value:
                continue  # cannot beat the incumbent on value; skip mode search
            for mode in config.MODES:
                p = completion_prob(battery_pct, subset, draws, mode, b_res)
                if p < threshold:
                    continue
                if best is None or (value, p) > (best.value, best.p_complete):
                    t_req_star = t_req_minutes(
                        subset, draws.speeds[mode], draws.carpet_coef, draws.dirt_coef
                    )
                    consumed = draws.rates[mode] * t_req_star
                    best = PlanResult(
                        zones=subset,
                        mode=mode,
                        p_complete=p,
                        t_req_min=float(np.median(t_req_star)),
                        value=value,
                        remaining_pct=max(float(battery_pct - np.median(consumed)), b_res),
                    )
    return best


def subset_feasible(
    battery_pct: float,
    zones: list[Zone],
    draws: JointDraws,
    b_res: float = config.B_RES_DEFAULT_PCT,
    threshold: float = config.P_SUFFICIENT,
) -> bool:
    """Whether ANY zone subset completes at ≥ threshold in some mode (§4.1 부족A vs 부족B).

    Early-exits on the first feasible (subset, mode) — this runs on every /api/predict, and
    only the existence of a completable subset matters here, not which one (that is best_subset).
    """
    for r in range(1, len(zones) + 1):
        for combo in combinations(range(len(zones)), r):
            subset = [zones[i] for i in combo]
            for mode in config.MODES:
                if completion_prob(battery_pct, subset, draws, mode, b_res) >= threshold:
                    return True
    return False


def rollout(
    zones_ordered: list[Zone],
    draws: JointDraws,
    mode: str,
    battery_pct: float,
    b_res: float,
    cells_frac: list[tuple[int, float]],
) -> tuple[list[float], np.ndarray]:
    """§5.2 trajectory rollout for one plan (zones in visit order).

    ``cells_frac`` is one (zone_pos, frac) per cleanable cell: ``zone_pos`` indexes
    ``zones_ordered`` and ``frac`` ∈ (0, 1] is the cell's position along that zone's sweep.
    Returns ``(zone_p, cell_p)`` — completion probability of each zone (all cells done) and of
    each cell — both over the shared draws, so they never contradict the banner (§1 principle 7).
    """
    rates = draws.rates[mode]  # (B,)
    speeds = draws.speeds[mode]  # (B,)
    carpet_coef = draws.carpet_coef  # (B,)
    dirt_coef = draws.dirt_coef  # (B,)
    budget = max(battery_pct - b_res, 0.0)
    k = len(zones_ordered)

    area = np.array([z.area_m2 for z in zones_ordered])[:, None]
    carpet = np.array([z.carpet_ratio for z in zones_ordered])[:, None]
    dirt = np.array([z.avg_dirt for z in zones_ordered])[:, None]

    # Speed-dependent clean time per zone (K, B); travel is fixed, paid once per zone entered.
    tau_clean = (area / speeds[None, :]) * (1 + carpet_coef[None, :] * carpet)
    tau_clean = tau_clean * (1 + dirt_coef[None, :] * dirt)
    clean_cum = np.cumsum(tau_clean, axis=0)  # inclusive of zone k
    clean_prev = clean_cum - tau_clean  # exclusive (work done before zone k)
    travel_finish = (np.arange(1, k + 1) * _TRAVEL_MIN_PER_ZONE)[:, None]  # (K, 1)

    consumed_zone = rates[None, :] * (clean_cum + travel_finish)  # (K, B)
    zone_p = (consumed_zone <= budget).mean(axis=1).tolist()

    pos = np.array([zp for zp, _ in cells_frac], dtype=int)
    frac = np.array([f for _, f in cells_frac], dtype=float)[:, None]
    cell_time = clean_prev[pos] + frac * tau_clean[pos] + (pos[:, None] + 1) * _TRAVEL_MIN_PER_ZONE
    cell_p = (rates[None, :] * cell_time <= budget).mean(axis=1)
    return zone_p, cell_p
