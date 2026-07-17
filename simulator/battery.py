"""Physics battery model (SPEC §2.4 a·b·d).

Load model + discharge with rate-dependent effective capacity and AR(1) within-session noise
(a·b), plus equivalent-full-cycle degradation (d). SoH is an input to a session; the generator
carries a lifetime EFC accumulator forward so the device ages across its history (§2.4d, §3.2).
Voltage/temperature channels (c) live in ``simulator/sensors.py``.

The AR(1) term exists so the rule model's "constant rate within a session" assumption is
NOT auto-satisfied by the simulator — evaluation keeps real-world difficulty (§2.4b).
"""

from backend.app import config

from .detrng import DetRNG


def efc_increment(dsoc_pct: float, mode: str) -> float:
    """§2.4d EFC contribution of one discharge step: ΔSoC/100 × w_mode."""
    return dsoc_pct / 100.0 * config.EFC_WEIGHT_BY_MODE[mode]


def soh_from_efc(efc: float) -> float:
    """§2.4d SoH = 1 − β·EFC, floored at 0.5 (well past the 80 % end-of-life mark)."""
    return max(0.5, 1.0 - config.DEGRADATION_BETA * efc)


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

    def __init__(self, rng: DetRNG, soh: float = 1.0):
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
