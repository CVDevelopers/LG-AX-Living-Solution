"""Subset planner (§5.1) and trajectory rollout (§5.2): value order, feasibility, consistency."""

import numpy as np

from backend.app import config
from backend.app.core.predict.bootstrap import JointDraws, draw_joint
from backend.app.core.predict.planner import (
    best_subset,
    completion_prob,
    rollout,
    subset_feasible,
    subset_value,
)
from backend.app.core.predict.types import Segment, Zone
from tests.conftest import make_stat

ZONES = [
    Zone(1, "거실", 16.0, 0.25, 50.0),
    Zone(2, "주방", 9.0, 0.0, 50.0),
    Zone(3, "침실", 12.0, 0.6, 60.0),
]


def _const_draws(rates: dict[str, float], speeds: dict[str, float], b: int = 400) -> JointDraws:
    """Variance-free draws → completion is a deterministic step in battery; selection is exact."""
    return JointDraws(
        rates={m: np.full(b, rates[m]) for m in config.MODES},
        speeds={m: np.full(b, speeds[m]) for m in config.MODES},
        carpet_coef=np.full(b, config.TREQ_CARPET_COEF),
        dirt_coef=np.full(b, config.TREQ_DIRT_COEF),
    )


def _history():
    segments = [Segment(a, "standard", 8.0 + 0.4 * (a % 3), 10.0) for a in range(12)]
    stats = [make_stat(age=a, dsoc=8.0 + 0.4 * (a % 3), duration=10.0, area=9.0) for a in range(12)]
    return segments, stats


def test_subset_value_is_dirt_weighted_area():
    assert subset_value([ZONES[0]]) == 16.0 * 1.5
    assert subset_value(ZONES) == sum(z.area_m2 * (1 + z.avg_dirt / 100) for z in ZONES)


def test_full_battery_plans_every_zone():
    draws = _const_draws({m: 0.5 for m in config.MODES}, {m: 2.0 for m in config.MODES})
    result = best_subset(100.0, ZONES, draws, b_res=5.0)
    assert result is not None
    assert {z.zone_id for z in result.zones} == {1, 2, 3}  # highest value = the whole set


def test_planner_picks_max_value_feasible_subset():
    # Cheap flat zones (2,3-ish) vs carpet-heavy zone 1; tight battery excludes the full set.
    draws = _const_draws({m: 1.0 for m in config.MODES}, {m: 1.0 for m in config.MODES})
    result = best_subset(22.0, ZONES, draws, b_res=4.0)
    assert result is not None
    assert result.p_complete >= config.P_SUFFICIENT
    # Whatever it chose must be the value-max among feasible subsets.
    from itertools import combinations

    feasible_values = [
        subset_value([ZONES[i] for i in combo])
        for r in range(1, len(ZONES) + 1)
        for combo in combinations(range(len(ZONES)), r)
        if any(
            completion_prob(22.0, [ZONES[i] for i in combo], draws, m, 4.0) >= config.P_SUFFICIENT
            for m in config.MODES
        )
    ]
    assert result.value == max(feasible_values)


def test_no_feasible_subset_returns_none():
    draws = _const_draws({m: 3.0 for m in config.MODES}, {m: 0.5 for m in config.MODES})
    assert best_subset(6.0, ZONES, draws, b_res=5.0) is None
    assert subset_feasible(6.0, ZONES, draws, b_res=5.0) is False


def test_feasibility_is_monotone_in_battery():
    draws = draw_joint(*_history(), np.random.default_rng(0))
    feas = [subset_feasible(b, ZONES, draws, b_res=4.0) for b in (8, 20, 40, 90)]
    assert feas == sorted(feas, key=int)  # once feasible, stays feasible as battery rises


def test_rollout_full_set_matches_banner_probability():
    """§5.2 identity: P(last zone finishes) ≡ §3.3 P_complete on the same draws (principle 7)."""
    draws = draw_joint(*_history(), np.random.default_rng(1))
    for mode in config.MODES:
        zone_p, _ = rollout(ZONES, draws, mode, 45.0, 4.0, [])
        p = completion_prob(45.0, ZONES, draws, mode, 4.0)
        assert abs(zone_p[-1] - p) <= 0.005, f"{mode}: rollout {zone_p[-1]} vs banner {p}"


def test_rollout_zone_completion_is_non_increasing_along_route():
    draws = draw_joint(*_history(), np.random.default_rng(2))
    zone_p, _ = rollout(ZONES, draws, "standard", 40.0, 4.0, [])
    assert zone_p == sorted(zone_p, reverse=True)  # later zones can only be less likely finished


def test_rollout_cell_probabilities_in_unit_range():
    draws = draw_joint(*_history(), np.random.default_rng(3))
    cells_frac = [(0, 0.5), (0, 1.0), (1, 0.5), (2, 1.0)]
    _, cell_p = rollout(ZONES, draws, "standard", 40.0, 4.0, cells_frac)
    assert cell_p.shape == (4,)
    assert np.all((cell_p >= 0.0) & (cell_p <= 1.0))
    # Within a zone, a later cell (higher frac) finishes no more often than an earlier one.
    assert cell_p[1] <= cell_p[0]
