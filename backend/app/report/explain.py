"""v1 rule factor decomposition (SPEC §3.6).

SHAP is applied to v2/v3 in M4; the v1 rule engine gets an equivalent contract via a *rule
factor decomposition* — attribute a session's consumption deviation from the nominal baseline to
per-term contributions using the very power-model coefficients the simulator used (§2.4a). Each
term is expressed in minutes of "consumed faster / slower" so the narrator (§9.5) and the "off
day" demo (§8.5) can cite it. Signs are physical by construction (carpet↑ / obstacles↑ / dirt↑ →
faster), so the §8.1 sign-consistency gate (≥95 %) holds exactly for the v1 path.
"""

from dataclasses import dataclass

from .. import config
from .facts import ReportFacts

_LABELS = {
    "obstacle": "장애물 회피",
    "carpet": "카펫 구역",
    "dirt": "오염도",
    "aging": "배터리 노화",
}


@dataclass(frozen=True)
class Factor:
    feature: str
    label: str
    direction: str  # "faster" (raised consumption rate) | "slower"
    contribution_min: float  # signed minutes of available-time change vs the nominal baseline


def explain_session(
    facts: ReportFacts, drift: float = 1.0, reference_min: float | None = None
) -> list[Factor]:
    """Top factors behind the session's consumption, most influential first (§3.6 top-3 contract).

    Contributions are attributed over ``reference_min`` (the session runtime for a post-hoc
    report; a forecast context would pass the predicted available time). Each factor's rate share
    × the reference gives "consumed as if N minutes longer/shorter than nominal".
    """
    mode = facts.mode
    p_susp = config.P_SUCTION_W[mode]
    f_dirt_base = 1.0 + config.F_DIRT_COEF * config.DIRT_MEAN  # nominal dirt term
    p_nom = (
        p_susp * f_dirt_base + config.P_DRIVE_W + config.P_AUX_W
    )  # hardfloor, mean dirt, no obstacle
    t_ref = facts.duration_min if reference_min is None else reference_min

    # Additive power deltas vs the nominal baseline (§2.4a), divided by nominal power → rate share.
    dp_dirt = p_susp * config.F_DIRT_COEF * (facts.avg_dirt - config.DIRT_MEAN)
    dp_carpet = facts.carpet_ratio * (
        (config.F_FLOOR_CARPET - 1.0) * p_susp * f_dirt_base
        + (config.G_FLOOR_CARPET - 1.0) * config.P_DRIVE_W
    )
    dp_obst = p_susp * f_dirt_base * config.F_OBST_COEF * facts.avoid_per_min
    shares = {
        "obstacle": dp_obst / p_nom,
        "carpet": dp_carpet / p_nom,
        "dirt": dp_dirt / p_nom,
        "aging": drift - 1.0,
    }

    factors = [
        Factor(
            feature=feat,
            label=_LABELS[feat],
            direction="faster" if share >= 0 else "slower",
            contribution_min=round(t_ref * share, 2),
        )
        for feat, share in shares.items()
    ]
    factors.sort(key=lambda f: abs(f.contribution_min), reverse=True)
    return factors
