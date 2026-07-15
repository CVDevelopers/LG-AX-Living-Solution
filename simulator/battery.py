"""Physics battery model v0 (SPEC §2.4 a·b).

M0 scope: load model + discharge with rate-dependent effective capacity and AR(1)
within-session noise. Degradation dynamics (d) and voltage/temperature channels (c)
arrive in M2 — SoH is accepted as a fixed input here.

The AR(1) term exists so the rule model's "constant rate within a session" assumption is
NOT auto-satisfied by the simulator — evaluation keeps real-world difficulty (§2.4b).
"""

import numpy as np

from backend.app import config


def suction_power_w(mode: str, on_carpet: bool, dirt: float, avoid_per_min: float) -> float:
    """P(t) = P_suction(mode)·f_floor·f_dirt·f_obst + P_drive·g_floor + P_aux (§2.4a)."""
    f_floor = config.F_FLOOR_CARPET if on_carpet else 1.0
    g_floor = config.G_FLOOR_CARPET if on_carpet else 1.0
    f_dirt = 1.0 + config.F_DIRT_COEF * dirt
    f_obst = 1.0 + config.F_OBST_COEF * avoid_per_min
    return (
        config.P_SUCTION_W[mode] * f_floor * f_dirt * f_obst
        + config.P_DRIVE_W * g_floor
        + config.P_AUX_W
    )


def travel_power_w() -> float:
    return config.P_DRIVE_W + config.P_AUX_W


class BatteryModel:
    """Stateful per-session discharge: ε_session fixed at start, ε_ar(t) evolves per minute."""

    P_STD_REF_W = config.P_SUCTION_W["standard"] + config.P_DRIVE_W + config.P_AUX_W

    def __init__(self, rng: np.random.Generator, soh: float = 1.0):
        self.rng = rng
        self.soh = soh
        self.eps_session = float(rng.normal(1.0, config.EPS_SESSION_SIGMA))
        self.eps_ar = 1.0

    def step_dsoc(self, power_w: float, dt_min: float = 1.0) -> float:
        """ΔSoC (positive %) consumed over dt_min at the given power (§2.4b)."""
        eta_rate = (power_w / self.P_STD_REF_W) ** (-config.ALPHA_RATE)
        self.eps_ar = (
            1.0
            + config.AR1_PHI * (self.eps_ar - 1.0)
            + float(self.rng.normal(0.0, config.AR1_SIGMA))
        )
        energy_wh = power_w * (dt_min / 60.0)
        dsoc = energy_wh / (config.E_NOM_WH * self.soh * eta_rate) * 100.0
        return dsoc * self.eps_session * self.eps_ar
