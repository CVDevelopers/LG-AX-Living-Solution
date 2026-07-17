"""Voltage/temperature/current channels (§2.4c): OCV shape, R_int, terminal solve, thermal."""

import numpy as np
import pytest

from backend.app import config
from simulator.detrng import DetRNG
from simulator.sensors import (
    MinuteState,
    ocv_pack,
    r_int,
    simulate_sensor_trace,
    terminal_voltage,
)


def test_ocv_breakpoints_and_monotonicity():
    assert ocv_pack(1.0) == pytest.approx(16.8)
    assert ocv_pack(0.85) == pytest.approx(15.8)
    assert ocv_pack(0.15) == pytest.approx(14.2)
    assert ocv_pack(0.0) == pytest.approx(12.0)
    socs = np.linspace(0, 1, 50)
    volts = [ocv_pack(s) for s in socs]
    assert volts == sorted(volts)  # OCV rises monotonically with SoC


def test_r_int_rises_with_aging_and_at_low_soc():
    assert r_int(0.5, 1.0) == pytest.approx(config.R_INT_R0_OHM)  # nominal, no knee
    assert r_int(0.5, 0.8) > r_int(0.5, 1.0)  # aging raises R
    assert r_int(0.02, 1.0) > r_int(0.5, 1.0)  # low-SoC knee raises R


def test_terminal_voltage_under_load_is_below_ocv():
    ocv = ocv_pack(0.5)
    v, i = terminal_voltage(ocv, power_w=40.0, r=0.12)
    assert v < ocv
    assert i == pytest.approx(40.0 / v)


def test_thermal_rises_with_load_and_channels_in_range():
    rng = DetRNG(5)
    minutes = [
        MinuteState(power_w=55.0, soc_start=80.0, soc_end=79.0, mode="turbo", wheel_speed_mps=0.2)
        for _ in range(20)
    ]
    trace = simulate_sensor_trace(minutes, soh=1.0, rng=rng, resolution_s=1)
    assert len(trace) == 20 * 60
    assert trace[-1].temp_c > trace[0].temp_c  # pack heats up under sustained load
    assert all(10.0 < s.voltage_v < 17.5 for s in trace)
    assert all(s.current_a > 0 for s in trace)  # discharging


def test_charging_current_is_negative():
    rng = DetRNG(6)
    minutes = [MinuteState(0.0, 20.0, 20.3, "standard", 0.0, charging=True)]
    trace = simulate_sensor_trace(minutes, soh=1.0, rng=rng, resolution_s=60)
    assert trace[0].current_a < 0


def test_sensor_trace_is_deterministic():
    minutes = [MinuteState(30.0, 50.0, 49.5, "standard", 0.2) for _ in range(5)]
    a = simulate_sensor_trace(minutes, 0.95, DetRNG(9), 1)
    b = simulate_sensor_trace(minutes, 0.95, DetRNG(9), 1)
    assert [s.voltage_v for s in a] == [s.voltage_v for s in b]
    assert [s.temp_c for s in a] == [s.temp_c for s in b]
