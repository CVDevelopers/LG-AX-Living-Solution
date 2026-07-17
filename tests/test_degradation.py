"""Degradation model (§2.4d): EFC accumulation and the SoH = 1 − β·EFC trajectory."""

import pytest

from simulator.battery import BatteryModel, efc_increment, soh_from_efc, suction_power_w
from simulator.detrng import DetRNG


def test_soh_from_efc_endpoints():
    assert soh_from_efc(0.0) == 1.0
    assert soh_from_efc(250.0) == pytest.approx(0.9)
    assert soh_from_efc(500.0) == pytest.approx(0.8)  # 500 full cycles → 80 % [R3][R6][R17]


def test_soh_floor():
    assert soh_from_efc(10_000.0) == 0.5  # clamped well past end-of-life


def test_efc_weight_ordering_by_mode():
    # Same ΔSoC costs more equivalent cycles in a harsher mode (§2.4d w_mode).
    assert (
        efc_increment(10.0, "eco") < efc_increment(10.0, "standard") < efc_increment(10.0, "turbo")
    )
    assert efc_increment(100.0, "eco") == pytest.approx(1.0)
    assert efc_increment(100.0, "standard") == pytest.approx(1.05)


def test_lifetime_efc_accumulates_and_soh_declines():
    # ~500 standard full cycles should land SoH near the 80 % end-of-life mark.
    efc = 0.0
    for _ in range(500):
        efc += efc_increment(100.0, "standard")
    soh = soh_from_efc(efc)
    assert 0.75 <= soh <= 0.82


def test_soh_scales_discharge_rate():
    """A lower SoH raises the discharge rate for the same load (§2.4b effective-capacity term)."""
    rng_a, rng_b = DetRNG(3), DetRNG(3)
    fresh = BatteryModel(rng_a, soh=1.0)
    aged = BatteryModel(rng_b, soh=0.8)
    fresh.eps_session = aged.eps_session = 1.0
    power = suction_power_w("standard", False, 0.0, 0.0)
    r_fresh = fresh.step_dsoc(power)
    r_aged = aged.step_dsoc(power)
    assert r_aged > r_fresh
    assert r_aged / r_fresh == pytest.approx(1.0 / 0.8, rel=0.02)
