"""Segment extraction (§3.1): mode-change and charge-resume sessions are refined, not dropped."""

import pytest

from backend.app.core.predict.segments import extract_session_segments
from tests.conftest import make_ticks


def test_single_mode_session_yields_one_segment():
    ticks = make_ticks([("standard", 0.8, 10)])
    segs = extract_session_segments(ticks, age=0)
    assert len(segs) == 1
    assert segs[0].mode == "standard"
    assert segs[0].dt_min == 10
    assert segs[0].rate == pytest.approx(0.8)


def test_mode_change_splits_into_two_segments():
    ticks = make_ticks([("standard", 0.8, 6), ("turbo", 1.3, 7)])
    segs = extract_session_segments(ticks, age=0)
    assert [(s.mode, s.dt_min) for s in segs] == [("standard", 6.0), ("turbo", 7.0)]
    assert segs[1].rate == pytest.approx(1.3)


def test_charging_interval_breaks_and_is_excluded():
    # 6 min discharge, 4 min charging (battery rising), 5 min discharge again.
    ticks = make_ticks([("standard", 0.8, 6)])
    battery = ticks[-1][1]
    t = ticks[-1][0]
    for _ in range(4):
        battery += 2.0
        t += 1
        ticks.append((t, battery, "standard", 1))
    for _ in range(5):
        battery -= 0.8
        t += 1
        ticks.append((t, battery, "standard", 0))
    segs = extract_session_segments(ticks, age=0)
    assert [s.dt_min for s in segs] == [6.0, 5.0]
    assert all(s.rate == pytest.approx(0.8) for s in segs)


def test_battery_bump_breaks_monotonicity():
    ticks = make_ticks([("standard", 0.8, 5)])
    battery, t = ticks[-1][1] + 1.5, ticks[-1][0] + 1  # spurious rise, charging flag 0
    ticks.append((t, battery, "standard", 0))
    ticks += [(t + i + 1, battery - 0.8 * (i + 1), "standard", 0) for i in range(4)]
    segs = extract_session_segments(ticks, age=0)
    assert [s.dt_min for s in segs] == [5.0, 4.0]


def test_short_runs_are_dropped():
    ticks = make_ticks([("standard", 0.8, 2), ("turbo", 1.3, 2)])
    assert extract_session_segments(ticks, age=0) == []


def test_time_gap_breaks_segment():
    ticks = make_ticks([("standard", 0.8, 4)])
    last_t, last_b = ticks[-1][0], ticks[-1][1]
    ticks += [(last_t + 3 + i, last_b - 0.8 * (i + 1), "standard", 0) for i in range(5)]
    segs = extract_session_segments(ticks, age=0)
    assert [s.dt_min for s in segs] == [4.0, 4.0]
