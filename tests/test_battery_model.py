"""Physics model (§2.4 a·b): power ordering, spec-anchored mean rates, discharge snapshot."""

import json
from pathlib import Path

import numpy as np
import pytest

from backend.app import config
from simulator.battery import BatteryModel, suction_power_w

GOLDEN = Path(__file__).parent / "golden" / "discharge_curve.json"


def test_power_ordering_across_modes():
    powers = [suction_power_w(m, False, 50.0, 0.0) for m in config.MODES]
    assert powers == sorted(powers)


def test_carpet_increases_power():
    hard = suction_power_w("standard", False, 0.0, 0.0)
    carpet = suction_power_w("standard", True, 0.0, 0.0)
    assert carpet > hard
    assert carpet == pytest.approx(28.0 * 1.30 + 5.0 * 1.15 + 2.0)


def test_mean_rates_match_reference_profile():
    """Hardfloor, dirt 0, SoH 1.0 → §2.4b reference rates 0.55/0.75/1.20 %/min within 5 %."""
    for mode, ref in config.R_PRIOR_PCT_MIN.items():
        rng = np.random.default_rng(99)
        model = BatteryModel(rng)
        model.eps_session = 1.0  # isolate the deterministic part
        power = suction_power_w(mode, False, 0.0, 0.0)
        rates = [model.step_dsoc(power) for _ in range(300)]
        assert np.mean(rates) == pytest.approx(ref, rel=0.05)


def test_ar1_noise_is_autocorrelated():
    rng = np.random.default_rng(7)
    model = BatteryModel(rng)
    power = suction_power_w("standard", False, 50.0, 0.0)
    rates = np.array([model.step_dsoc(power) for _ in range(500)])
    d = rates - rates.mean()
    autocorr = float((d[1:] * d[:-1]).sum() / (d**2).sum())
    assert autocorr > 0.5  # φ = 0.8 AR(1) must show through


def test_discharge_curve_snapshot():
    """Fixed-seed 30-minute standard-mode curve pinned to a committed golden file (§8.3)."""
    rng = np.random.default_rng(config.DEMO_SEED)
    model = BatteryModel(rng)
    power = suction_power_w("standard", False, 50.0, 0.0)
    battery, curve = 100.0, [100.0]
    for _ in range(30):
        battery -= model.step_dsoc(power)
        curve.append(round(battery, 4))
    expected = json.loads(GOLDEN.read_text())
    assert curve == pytest.approx(expected, abs=1e-4)
