"""Calibration fits and the §2.5 adoption gate (against committed literature anchors)."""

from backend.app import config
from simulator import calibrate


def _anchors():
    return calibrate.load_anchors()


def test_no_raw_datasets_present_by_default():
    # data/datasets/ holds only the tracked README — calibration runs in validation mode (§2.5).
    assert calibrate.raw_datasets_present() is False


def test_anchors_have_required_series():
    a = _anchors()
    assert a["ocv_cell"] and a["rate_capacity"] and a["cycle_soh"]
    assert "provenance" in a


def test_ocv_fit_within_gate():
    ocv = calibrate.fit_ocv(_anchors())
    assert ocv["passes"] is True
    assert ocv["rmse_mv"] <= config.CALIB_OCV_RMSE_MAX_MV
    # the default reference-profile curve is itself within tolerance of the anchors
    assert ocv["default_rmse_mv"] <= config.CALIB_OCV_RMSE_MAX_MV
    assert len(ocv["fitted_pack_v"]) == len(config.OCV_CURVE)


def test_alpha_ci_excludes_zero():
    alpha = calibrate.fit_alpha(_anchors())
    assert alpha["passes"] is True
    lo, hi = alpha["ci95"]
    assert lo > 0.0  # capacity strictly falls with C-rate → α CI clears 0
    assert alpha["alpha"] > 0.0


def test_beta_within_range():
    beta = calibrate.fit_beta(_anchors())
    assert beta["passes"] is True
    lo, hi = config.CALIB_BETA_RANGE
    assert lo <= beta["beta"] <= hi


def test_alpha_fit_is_deterministic():
    a1 = calibrate.fit_alpha(_anchors())
    a2 = calibrate.fit_alpha(_anchors())
    assert a1 == a2  # fixed bootstrap seed (§12.2)


def test_gate_all_three_pass_on_anchors():
    a = _anchors()
    ocv, alpha, beta = calibrate.fit_ocv(a), calibrate.fit_alpha(a), calibrate.fit_beta(a)
    assert ocv["passes"] and alpha["passes"] and beta["passes"]
