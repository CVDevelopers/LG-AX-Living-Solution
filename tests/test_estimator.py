"""base×drift estimator (§3.2): hand-computed cases, n_eff, cold-start prior convergence."""

import numpy as np
import pytest

from backend.app.core.predict.estimator import fit_estimator, kish_n_eff, segment_weights
from backend.app.core.predict.types import Segment


def test_case_a_single_segment_shrinks_toward_prior_and_shares_drift():
    # One std segment, age 0, dt 10, rate 0.9. Prior std = 0.75, k = 3.
    fit = fit_estimator([Segment(0, "standard", 9.0, 10.0)])
    assert fit.base["standard"] == pytest.approx((1 * 0.9 + 3 * 0.75) / 4)  # 0.7875
    assert fit.drift == pytest.approx(0.9 / 0.7875)  # 1.142857
    assert fit.r_tilde["standard"] == pytest.approx(0.9)
    # Shared drift propagates to a never-used stratum (eco prior 0.55).
    assert fit.r_tilde["eco"] == pytest.approx(0.55 * 0.9 / 0.7875)


def test_case_b_two_segments_age_decay_hand_computed():
    # std: (age 0, rate 0.8, dt 10) and (age 10, rate 0.6, dt 10).
    fit = fit_estimator([Segment(0, "standard", 8.0, 10.0), Segment(10, "standard", 6.0, 10.0)])
    # w40 = [1, 0.5^(10/40)]: r̂ = 0.708643, Kish n_eff = 1.985177
    assert fit.n_eff_by_mode["standard"] == pytest.approx(1.98518, abs=1e-4)
    assert fit.base["standard"] == pytest.approx(0.73353, abs=1e-4)
    assert fit.drift == pytest.approx(0.99973, abs=1e-4)
    assert fit.r_tilde["standard"] == pytest.approx(0.73333, abs=1e-4)


def test_case_c_drift_propagates_aging_to_unused_turbo():
    # std and eco both consuming 20 % above prior → drift 1.142857 exactly.
    fit = fit_estimator([Segment(0, "standard", 9.0, 10.0), Segment(0, "eco", 6.6, 10.0)])
    assert fit.drift == pytest.approx(1.142857, abs=1e-5)
    assert fit.r_tilde["turbo"] == pytest.approx(1.20 * 1.142857, abs=1e-4)


def test_n_eff_kish():
    segs = [Segment(0, "standard", 8.0, 10.0) for _ in range(4)]
    assert fit_estimator(segs).n_eff == pytest.approx(4.0)
    assert kish_n_eff(np.array([])) == 0.0


def test_segment_weights_length_and_age():
    w = segment_weights([Segment(0, "standard", 8.0, 10.0), Segment(10, "standard", 4.0, 5.0)])
    assert w[0] == pytest.approx(1.0)
    assert w[1] == pytest.approx(0.933**10 * 0.5)


def test_cold_start_converges_to_prior():
    fit = fit_estimator([])
    assert fit.base == {"eco": 0.55, "standard": 0.75, "turbo": 1.20}
    assert fit.drift == 1.0
    assert fit.n_eff == 0.0
