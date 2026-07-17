"""Report facts, §3.6 rule factor decomposition (sign consistency), §9.6 narration + guardrail."""

from dataclasses import replace

from backend.app.report import explain_session, narrate, numbers_supported
from backend.app.report.facts import ReportFacts

BASE = ReportFacts(
    session_id="S1",
    started_at="2026-05-29T09:00",
    mode="standard",
    start_battery=60.0,
    end_battery=45.0,
    dsoc=15.0,
    duration_min=20.0,
    cleaned_area_m2=30.0,
    carpet_ratio=0.2,
    obstacle_hits=4,
    avoid_per_min=0.2,
    dock_returns=0,
    mode_changes=0,
    completed=1,
    charged=False,
    soh_at_run=0.95,
    zones=[],
    avg_dirt=50.0,
    high_obstacle=False,
)


def _by_feature(facts, drift=1.0):
    return {f.feature: f for f in explain_session(facts, drift)}


def test_factor_signs_are_physical():
    # §3.6 sanity: carpet↑, obstacles↑, dirt↑ all raise consumption → positive (faster).
    f = _by_feature(replace(BASE, carpet_ratio=0.6, avoid_per_min=0.9, avg_dirt=70.0), drift=1.08)
    assert f["carpet"].contribution_min > 0 and f["carpet"].direction == "faster"
    assert f["obstacle"].contribution_min > 0 and f["obstacle"].direction == "faster"
    assert f["dirt"].contribution_min > 0 and f["dirt"].direction == "faster"
    assert f["aging"].contribution_min > 0  # drift > 1


def test_dirt_below_mean_is_slower():
    f = _by_feature(replace(BASE, avg_dirt=30.0))
    assert f["dirt"].contribution_min < 0 and f["dirt"].direction == "slower"


def test_carpet_contribution_monotone():
    lo = _by_feature(replace(BASE, carpet_ratio=0.1))["carpet"].contribution_min
    hi = _by_feature(replace(BASE, carpet_ratio=0.7))["carpet"].contribution_min
    assert hi > lo


def test_factors_sorted_by_magnitude():
    factors = explain_session(replace(BASE, carpet_ratio=0.6, avoid_per_min=0.9), drift=1.05)
    mags = [abs(f.contribution_min) for f in factors]
    assert mags == sorted(mags, reverse=True)
    assert len(factors) == 4


def _n_sentences(text: str) -> int:
    return len(text.split(". "))


def test_narration_is_three_to_five_sentences_and_guardrail_clean():
    out = narrate(BASE, explain_session(BASE, drift=1.05))
    assert 3 <= _n_sentences(out["text"]) <= 5
    assert out["guardrail_ok"] is True


def test_guardrail_flags_fabricated_number():
    assert numbers_supported("배터리 15% 사용했어요", {15.0}) is True
    assert numbers_supported("배터리 77% 사용했어요", {15.0}) is False


def test_anomaly_narration_cites_obstacle_cause():
    anomaly = replace(BASE, avoid_per_min=1.5, obstacle_hits=30, high_obstacle=True)
    out = narrate(anomaly, explain_session(anomaly, drift=1.0))
    assert out["top_factor"] == "obstacle"
    assert "장애물" in out["text"]
    assert out["guardrail_ok"] is True


def test_charged_session_skips_numeric_cause():
    charged = replace(BASE, charged=True, dock_returns=1)
    out = narrate(charged, explain_session(charged, drift=1.05))
    assert (
        "평소보다" not in out["text"]
    )  # no single-factor attribution over charge-inflated runtime
    assert "충전" in out["text"]
    assert out["guardrail_ok"] is True
