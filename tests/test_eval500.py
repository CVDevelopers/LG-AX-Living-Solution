"""Eval harness (§8.1, §8.5): metric structure, ablation ordering, reliability, segment refinement.

Runs a small in-memory slice (no file writes) so it stays inside the pytest budget; the full
500-session run is the scheduled job (§12.3).
"""

import pytest

from backend.app import config
from eval import eval500


@pytest.fixture(scope="module")
def metrics():
    m, _ = eval500.run(per_slice=24, hist_n=30)
    return m


def test_headline_metrics_present_and_sane(metrics):
    h = metrics["headline"]
    for key in (
        "time_mae_decision_band_min",
        "time_mae_overall_min",
        "treq_mae_min",
        "mape_pct",
        "coverage_pct",
        "state_agreement_pct",
    ):
        assert key in h
    assert 0.0 < h["mape_pct"] < 25.0  # rate error is scale-free and should be modest
    assert 40.0 <= h["coverage_pct"] <= 100.0
    assert h["state_agreement_pct"] >= 80.0


def test_ablation_has_stages_and_drift_helps(metrics):
    stages = {r["stage"]: r["time_mae"] for r in metrics["ablation"]}
    assert set(stages) == {"raw", "+ewma", "+shrink", "+drift"}
    # Shared drift (§3.2) is the decisive component under aging — it beats the drift-less stages.
    assert stages["+drift"] <= stages["raw"]
    assert stages["+drift"] <= stages["+shrink"]
    assert stages["+drift"] == min(stages.values())


def test_reliability_bins_cover_unit_interval(metrics):
    rel = metrics["reliability"]
    assert len(rel) == config.RELIABILITY_BINS
    assert sum(b["n"] for b in rel) > 0
    # in populated bins predicted and observed both stay in [0, 1]
    for b in rel:
        if b["observed"] is not None:
            assert 0.0 <= b["observed"] <= 1.0
            assert 0.0 <= b["predicted"] <= 1.0


def test_segment_refinement_contaminated_close_to_clean(metrics):
    """§3.1: contaminated sessions contribute clean segments — their rate MAPE ≈ clean's."""
    hs = metrics["hardened_slices"]
    clean = hs["clean_seg_mape"]["mape_pct"]
    for slice_key in ("mode_change_seg_mape", "resume_seg_mape"):
        if hs[slice_key]["n"] > 0:
            assert hs[slice_key]["mape_pct"] <= clean * 2.0 + 5.0  # comparable, not corrupted


def test_holdout_generalizes(metrics):
    hs = metrics["hardened_slices"]
    ratio = hs["holdout_over_train_ratio"]
    # The decision-band holdout slice is tiny at smoke scale (noisy); only assert with enough n.
    # The committed full run (per_slice=100) lands this at ~1.04.
    if ratio is not None and hs["holdout_maps_mae"]["n"] >= 8:
        assert ratio <= 1.5  # unlearned maps not dramatically worse than train maps
