"""Probability-currency state decision (SPEC §4.1).

Thresholds: sufficient at P ≥ 0.90 (same currency as the interval's nominal level),
caution while any mode reaches P ≥ 0.80. Schmitt hysteresis: promotion happens at the
nominal threshold, demotion only once P falls 5 %p below it — so 92 % always reads
"sufficient" while readings hovering near a boundary cannot oscillate.

M0 note: without the M1 subset planner, every insufficient case is SHORTAGE_B;
SHORTAGE_A ("some zone subset still completes") is refined in M1 (§5.1).
"""

from ... import config as cfg

SUFFICIENT = "sufficient"
CAUTION = "caution"
SHORTAGE_A = "shortage_a"
SHORTAGE_B = "shortage_b"

_RANK = {SUFFICIENT: 3, CAUTION: 2, SHORTAGE_A: 1, SHORTAGE_B: 1}


def decide_state(
    p_cur: float,
    p_by_mode: dict[str, float],
    n_eff: float,
    battery_pct: float,
    prev_state: str | None = None,
) -> tuple[str, str | None]:
    """Return (state, recommended_mode)."""
    p_max = max(p_by_mode.values())
    best_mode = max(p_by_mode, key=p_by_mode.get)

    if battery_pct <= cfg.B_RES_DEFAULT_PCT:
        state = SHORTAGE_B
    elif p_cur >= cfg.P_SUFFICIENT:
        state = SUFFICIENT
    elif p_max >= cfg.P_CAUTION:
        state = CAUTION
    else:
        state = SHORTAGE_B

    # Schmitt band: keep the previous (better) state while within θ − 5 %p of its threshold.
    if (
        prev_state in _RANK
        and _RANK[prev_state] > _RANK[state]
        and battery_pct > cfg.B_RES_DEFAULT_PCT
    ):
        if prev_state == SUFFICIENT and p_cur >= cfg.P_SUFFICIENT - cfg.HYSTERESIS_PCT_PT:
            state = SUFFICIENT
        elif prev_state == CAUTION and p_max >= cfg.P_CAUTION - cfg.HYSTERESIS_PCT_PT:
            state = CAUTION

    # Low data caps optimism: n_eff < 5 can never claim "sufficient" (§3.2, §4.1).
    if n_eff < cfg.N_EFF_LOW and state == SUFFICIENT:
        state = CAUTION

    recommend = best_mode if state == CAUTION and p_by_mode[best_mode] >= cfg.P_CAUTION else None
    return state, recommend
