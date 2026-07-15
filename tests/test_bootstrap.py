"""Joint bootstrap (§3.2–3.3): fixed-seed reproducibility and T*–T_req* coupling."""

import numpy as np

from backend.app.core.predict import predict
from backend.app.core.predict.bootstrap import draw_joint, t_est_minutes, t_req_minutes
from backend.app.core.predict.types import Segment
from tests.conftest import make_stat, make_zones


def _history():
    segments = [Segment(a, "standard", 8.0 + 0.4 * (a % 3), 10.0) for a in range(12)]
    stats = [make_stat(age=a, dsoc=8.0 + 0.4 * (a % 3), duration=10.0, area=9.0) for a in range(12)]
    return segments, stats


def test_fixed_seed_reproducibility():
    segments, stats = _history()
    zones = make_zones()
    out1 = predict(50.0, "standard", zones, segments, stats)
    out2 = predict(50.0, "standard", zones, segments, stats)
    assert out1 == out2


def test_draws_differ_across_seeds():
    segments, stats = _history()
    d1 = draw_joint(segments, stats, np.random.default_rng(1))
    d2 = draw_joint(segments, stats, np.random.default_rng(2))
    assert not np.allclose(d1.rates["standard"], d2.rates["standard"])


def test_interval_ordering_and_probability_bounds():
    segments, stats = _history()
    out = predict(50.0, "standard", make_zones(), segments, stats)
    assert out["t_lo_min"] <= out["t_est_min"] <= out["t_hi_min"]
    assert out["t_req_lo"] <= out["t_req_hi"]
    assert 0.0 <= out["p_complete"] <= 1.0


def test_joint_draws_are_correlated():
    """A slow high-consumption session must push T* down AND T_req* up in the same draw."""
    segments, stats = [], []
    for a in range(16):
        heavy = a % 2 == 0
        rate = 0.95 if heavy else 0.60  # around a ~0.775 fitted point
        speed_area = 8.0 if heavy else 14.0  # 10-min sessions → v ≈ 0.8 vs 1.4 m²/min
        segments.append(Segment(a, "standard", rate * 10, 10.0))
        stats.append(make_stat(age=a, dsoc=rate * 10, duration=10.0, area=speed_area, carpet=0.0))
    draws = draw_joint(segments, stats, np.random.default_rng(0))
    t = t_est_minutes(50.0, draws.rates["standard"])
    t_req = t_req_minutes(
        make_zones(), draws.speeds["standard"], draws.carpet_coef, draws.dirt_coef
    )
    corr = float(np.corrcoef(t, t_req)[0, 1])
    assert corr < -0.3, f"expected strong negative coupling, got {corr}"


def test_completion_probability_monotone_in_battery():
    segments, stats = _history()
    zones = make_zones()
    p = [
        predict(b, "standard", zones, segments, stats)["p_complete"]
        for b in (20.0, 40.0, 60.0, 90.0)
    ]
    assert p == sorted(p)


def test_cold_start_flags_low_data():
    out = predict(80.0, "standard", make_zones(), [], [])
    assert out["basis"]["low_data"] is True
    assert out["basis"]["n_eff"] == 0.0
    assert out["state"] != "sufficient"  # capped at caution (§4.1)


def test_battery_at_reserve_is_shortage():
    segments, stats = _history()
    out = predict(5.0, "standard", make_zones(), segments, stats)
    assert out["state"] == "shortage_b"
    assert out["t_est_min"] == 0.0
    assert out["p_complete"] == 0.0
