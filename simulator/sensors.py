"""Voltage / current / temperature sensor channels (SPEC §2.4c) — offline lab.

Given a session's per-minute load trace, produce the ``sensor_ticks`` rows a real pack would
log (§2.3): terminal voltage from a 3-region OCV curve minus the IR drop, current solved from
the load, and pack temperature from a first-order thermal model. Channels are logged at 1 s for
the most recent sessions and summarised to 1 min for older ones (§2.3 retention).

The prediction engine never reads these channels (§1 principle 1); they feed the sim-vs-measured
calibration overlay (§2.5, §8.5) and are the raw material for the M4 LSTM's V/T features (§3.5).

All noise goes through DetRNG (fixed two-uniform Box–Muller) so the stream stays reproducible
across numpy versions and CPU platforms (§12.2). Every stored float is rounded to ≤4 decimals,
matching the canonical-hash quantisation.
"""

import math
from dataclasses import dataclass

from backend.app import config

from .detrng import DetRNG

# Reference peak load (turbo suction on carpet + drive + aux) — normaliser for the PWM-duty channel.
_P_MAX_W = config.P_SUCTION_W["turbo"] * config.F_FLOOR_CARPET + config.P_DRIVE_W + config.P_AUX_W
# CC charge power from the ≤6 h full-charge spec (§2.1): %/min × Wh/% × 60.
_CHARGE_POWER_W = config.CHARGE_RATE_PCT_MIN * config.WH_PER_SOC_PCT * 60.0


@dataclass(frozen=True)
class MinuteState:
    """One minute of the session as the sensor model needs to see it."""

    power_w: float  # instantaneous load (discharge > 0); ignored when charging
    soc_start: float  # %SoC at the minute's start
    soc_end: float  # %SoC at the minute's end
    mode: str
    wheel_speed_mps: float
    charging: bool = False
    event: str | None = None


@dataclass(frozen=True)
class SensorSample:
    t_sec: int
    voltage_v: float
    current_a: float
    temp_c: float
    motor_pwm: float
    wheel_speed_mps: float
    event: str | None


def ocv_pack(soc_frac: float) -> float:
    """Piecewise-linear open-circuit pack voltage at ``soc_frac`` ∈ [0, 1] (§2.4c)."""
    soc = min(1.0, max(0.0, soc_frac))
    curve = config.OCV_CURVE  # descending SoC breakpoints (soc, volts)
    for (s_hi, v_hi), (s_lo, v_lo) in zip(curve, curve[1:], strict=False):
        if soc >= s_lo:
            frac = (soc - s_lo) / (s_hi - s_lo)
            return v_lo + frac * (v_hi - v_lo)
    return curve[-1][1]


def r_int(soc_frac: float, soh: float) -> float:
    """Internal pack resistance: aging and low SoC both raise it (§2.4c) [R14][R15][R16]."""
    knee = max(0.0, config.R_INT_KNEE_SOC - soc_frac) / config.R_INT_KNEE_SOC
    return (
        config.R_INT_R0_OHM
        * (1.0 + config.R_INT_SOH_COEF * (1.0 - soh))
        * (1.0 + config.R_INT_KNEE_COEF * knee)
    )


def terminal_voltage(ocv: float, power_w: float, r: float) -> tuple[float, float]:
    """Solve V = OCV − I·R with I = P/V for the discharge terminal voltage and current.

    V² − OCV·V + P·R = 0 → V = (OCV + √(OCV² − 4·P·R)) / 2 (upper root = physical branch).
    """
    disc = ocv * ocv - 4.0 * power_w * r
    voltage = (ocv + math.sqrt(disc)) / 2.0 if disc > 0 else ocv / 2.0
    current = power_w / voltage if voltage > 0 else 0.0
    return voltage, current


def _pwm(power_w: float) -> float:
    return min(100.0, max(0.0, power_w / _P_MAX_W * 100.0))


def simulate_sensor_trace(
    minutes: list[MinuteState],
    soh: float,
    rng: DetRNG,
    resolution_s: int = 1,
) -> list[SensorSample]:
    """Roll the thermal state forward and emit a SensorSample every ``resolution_s`` seconds.

    ``resolution_s = 1`` → raw 1 s log; ``resolution_s = 60`` → the 1 min summary kept for older
    sessions (§2.3). Temperature integrates continuously across the whole session; V/I are
    instantaneous. Noise is applied per emitted sample (§2.4c).
    """
    temp = config.TEMP_AMB_C
    out: list[SensorSample] = []
    for i, m in enumerate(minutes):
        for s in range(0, 60, resolution_s):
            frac = s / 60.0
            soc_pct = m.soc_start + (m.soc_end - m.soc_start) * frac
            soc_frac = soc_pct / 100.0
            ocv = ocv_pack(soc_frac)
            r = r_int(soc_frac, soh)
            if m.charging:
                i_charge = _CHARGE_POWER_W / max(ocv, 1e-6)
                voltage = ocv + i_charge * r
                current = -i_charge
                heat_w = _CHARGE_POWER_W * 0.3  # charging dissipates far less than the CC load
            else:
                voltage, current = terminal_voltage(ocv, m.power_w, r)
                heat_w = m.power_w
            # First-order thermal model dT = (P·coef − (T−T_amb)/τ)·dt, dt in minutes (§2.4c).
            dt_min = resolution_s / 60.0
            temp += (
                heat_w * config.TEMP_RISE_COEF
                - (temp - config.TEMP_AMB_C) / config.TEMP_DECAY_TAU_MIN
            ) * dt_min
            v_obs = voltage + rng.normal(0.0, config.V_NOISE_V)
            i_obs = current * (1.0 + rng.normal(0.0, config.I_NOISE_FRAC))
            t_obs = temp + rng.normal(0.0, config.T_NOISE_C)
            out.append(
                SensorSample(
                    t_sec=i * 60 + s,
                    voltage_v=round(v_obs, 4),
                    current_a=round(i_obs, 4),
                    temp_c=round(t_obs, 4),
                    motor_pwm=round(_pwm(m.power_w) if not m.charging else 0.0, 2),
                    wheel_speed_mps=round(m.wheel_speed_mps, 4),
                    event=m.event if s == 0 else None,
                )
            )
    return out
