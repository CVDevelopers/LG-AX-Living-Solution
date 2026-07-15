"""State machine (§4.1): thresholds, Schmitt hysteresis, low-data cap, reserve boundary."""

from backend.app.core.predict.state import (
    CAUTION,
    SHORTAGE_B,
    SUFFICIENT,
    decide_state,
)

P = {"eco": 0.95, "standard": 0.85, "turbo": 0.60}


def test_sufficient_at_nominal_threshold():
    state, rec = decide_state(0.92, {"eco": 0.92, "standard": 0.92, "turbo": 0.9}, 20, 50)
    assert state == SUFFICIENT and rec is None


def test_caution_recommends_best_mode():
    state, rec = decide_state(0.85, P, 20, 50)
    assert state == CAUTION and rec == "eco"


def test_shortage_when_no_mode_reaches_080():
    state, rec = decide_state(0.5, {"eco": 0.7, "standard": 0.5, "turbo": 0.3}, 20, 50)
    assert state == SHORTAGE_B and rec is None


def test_hysteresis_keeps_sufficient_within_band():
    assert decide_state(0.86, P, 20, 50, prev_state=SUFFICIENT)[0] == SUFFICIENT
    assert decide_state(0.84, P, 20, 50, prev_state=SUFFICIENT)[0] == CAUTION


def test_hysteresis_keeps_caution_within_band():
    low = {"eco": 0.76, "standard": 0.5, "turbo": 0.3}
    assert decide_state(0.5, low, 20, 50, prev_state=CAUTION)[0] == CAUTION
    lower = {"eco": 0.74, "standard": 0.5, "turbo": 0.3}
    assert decide_state(0.5, lower, 20, 50, prev_state=CAUTION)[0] == SHORTAGE_B


def test_promotion_needs_nominal_threshold():
    assert decide_state(0.90, P | {"eco": 0.9}, 20, 50, prev_state=CAUTION)[0] == SUFFICIENT
    assert decide_state(0.89, P, 20, 50, prev_state=CAUTION)[0] == CAUTION


def test_low_data_caps_at_caution():
    assert decide_state(0.99, {m: 0.99 for m in P}, 3, 50)[0] == CAUTION


def test_reserve_battery_forces_shortage():
    assert decide_state(0.99, {m: 0.99 for m in P}, 20, 4.0)[0] == SHORTAGE_B
    assert decide_state(0.99, {m: 0.99 for m in P}, 20, 4.0, prev_state=SUFFICIENT)[0] == SHORTAGE_B
