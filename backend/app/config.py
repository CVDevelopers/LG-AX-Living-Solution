"""Single home for every project constant (SPEC §1 principle 4).

Each constant carries its rationale: a [Rn] literature reference (see SPEC §14),
a SPEC section, or an explicit "[modeling choice]". Calibration output
``data/calibration/calibrated.json`` overrides matching keys at load time when
the §2.5 adoption gate passed; absent file → defaults below.
"""

import json
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# ── Runtime / deployment ─────────────────────────────────────────────────────
DB_PATH = Path(os.environ.get("BWF_DB_PATH", REPO_ROOT / "data" / "demo.db"))
IS_VERCEL = bool(os.environ.get("VERCEL"))  # profile W: read-only DB, /api/simulate off (§12.1)
CORS_ORIGINS = [
    "http://localhost:5173",  # Vite dev server (§6)
    os.environ.get("BWF_DEPLOY_ORIGIN", ""),  # Vercel production origin (§12.1)
]
PREDICT_SEED = 42  # fixed RNG seed → deterministic /api/predict for golden files (§8.3)

# ── Battery pack — reference profile "RVC-Ref" (§2.1) ───────────────────────
E_NOM_WH = 76.96  # Li-ion 4S 14.8 V × 5,200 mAh [R1][R2]
WH_PER_SOC_PCT = E_NOM_WH / 100.0  # 0.77 Wh per %SoC (§2.1)

# ── Load model P(t) (§2.4a) ──────────────────────────────────────────────────
P_SUCTION_W = {
    "eco": 18.0,
    "standard": 28.0,
    "turbo": 46.0,
}  # back-solved (§2.4b); 30–50 W [R5], max 55 W [R4]
P_DRIVE_W = 5.0  # constant drive load share (§2.4a)
P_AUX_W = 2.0  # electronics/sensors share (§2.4a)
F_FLOOR_CARPET = 1.30  # carpet suction boost, center of +20–40 % battery [R8]
G_FLOOR_CARPET = 1.15  # carpet drive resistance [R3][R9]
F_DIRT_COEF = 0.003  # f_dirt = 1 + 0.003·dirt  [modeling choice]
F_OBST_COEF = 0.05  # f_obst = 1 + 0.05·avoidances/min  [modeling choice]

# ── Discharge model (§2.4b) ──────────────────────────────────────────────────
ALPHA_RATE = 0.05  # η_rate = (P̄_mode/P_std)^(−α); refit against UNIBO in M2 (§2.5) [R10][R11][R12]
EPS_SESSION_SIGMA = 0.04  # ε_session ~ N(1, 0.04²), fixed per session (§2.4b)
AR1_PHI = 0.8  # within-session AR(1) noise (§2.4b)
AR1_SIGMA = 0.03  # AR(1) innovation σ (§2.4b)

# ── Coverage / motion (simulator v0 + T_req inversion) ──────────────────────
V_COVER_M2_MIN = {
    "eco": 0.90,
    "standard": 1.00,
    "turbo": 1.10,
}  # ≈1 m²/min class coverage; 60 m²·std ≈ 60 min → session −45 % ≈ [R13]  [modeling choice]
CARPET_SPEED_FACTOR = 0.8  # slower on carpet [R9] → ≈1.6× energy per m² (§2.4a)
V_TRAVEL_M_MIN = 18.0  # ≈0.3 m/s transit speed  [modeling choice]
TRAVEL_M_PER_ZONE = (
    3.0  # v0 zone-transition path estimate; real path in M1 (§3.3)  [modeling choice]
)
OBST_AVOID_PER_MIN = (
    0.3  # v0 mean avoidance events/min on obstacle-bearing zones  [modeling choice]
)
LOW_BATT_RETURN_PCT = 8.0  # dock return trigger, SoC < 8 % [R3] (§2.6)

# ── Reference consumption priors r_prior (§2.4b → §3.2, prior_source: reference) ──
R_PRIOR_PCT_MIN = {
    "eco": 0.55,
    "standard": 0.75,
    "turbo": 1.20,
}  # hardfloor, SoH 1.0; implies 182/133/83 min vs 180 [R1] / 140 [R4]
PRIOR_SOURCE = "reference"  # reference | federated (§11.2 — fedsim arrives M5)

# ── Estimator (§3.1–3.2) ─────────────────────────────────────────────────────
SEG_MIN_LEN_MIN = 3  # homogeneous segment minimum length (§3.1)
SEG_LEN_NORM_MIN = 10.0  # w_j length term Δt/10 (§3.1)
LAMBDA_AGE = 0.933  # session-age decay in w_j, half-life 10 sessions (§3.1)
HALFLIFE_BASE_SESSIONS = 40.0  # per-stratum base rate EWMA (§3.2)
HALFLIFE_DRIFT_SESSIONS = 10.0  # shared drift EWMA (§3.2)
SHRINK_K = 3.0  # prior pseudo-count k in shrunk EWMA (§3.2)
N_EFF_LOW = 5.0  # n_eff < 5 → low-data flag + state capped at 'caution' (§3.2, §4.1)

# ── Joint bootstrap (§3.2–3.3) ───────────────────────────────────────────────
BOOTSTRAP_B = 1000  # draws (§3.2)
INTERVAL_LO_PCT = 5  # [T_lo, T_hi] = [p5, p95] (§3.2)
INTERVAL_HI_PCT = 95
B_RES_DEFAULT_PCT = 5.0  # reserve battery; dynamic clamp(p95+2, 3, 8) arrives in M1 (§3.2)
TREQ_CARPET_COEF = 0.6  # T_req zone carpet factor (§3.3)
TREQ_DIRT_COEF = 0.003  # T_req zone dirt factor (§3.3)
TREQ_CARPET_COEF_SIGMA = (
    0.05  # per-draw coefficient noise, shared within draw (§3.3)  [modeling choice]
)
TREQ_DIRT_COEF_SIGMA = 0.0005  # [modeling choice]

# ── Charging (§2.1) ──────────────────────────────────────────────────────────
CHARGE_RATE_PCT_MIN = 100.0 / 360.0  # CC-CV full charge ≤ 6 h [R4] → ≈0.28 %/min

# ── State machine (§4.1) ─────────────────────────────────────────────────────
P_SUFFICIENT = 0.90  # same currency as the interval's nominal level (§4.1)
P_CAUTION = 0.80  # action (mode-switch) threshold (§4.1)
HYSTERESIS_PCT_PT = 0.05  # Schmitt band: demotion only below θ−5 %p (§4.1)

# ── Simulator session mix — M0 augmentation subset (§2.6) ────────────────────
START_SOC_FULL_PROB = 0.6  # {100 %: 0.6, U(50,95): 0.4}
START_SOC_PARTIAL_RANGE = (50.0, 95.0)
MODE_MIX = {"eco": 0.3, "standard": 0.5, "turbo": 0.2}  # household pattern (§2.6)
MODE_CHANGE_SESSION_PROB = 0.10  # one mid-session mode change in 10 % of sessions (§2.6)
DIRT_MEAN, DIRT_SIGMA = 50.0, 20.0  # zone dirt ~ clip(N(50, 20²), 0, 100) (§2.6)
FULL_CLEAN_PROB = 0.5  # v0: half full cleans, half partial zone subsets  [modeling choice]

# ── Data set sizing (§2.7) ───────────────────────────────────────────────────
HISTORY_SESSIONS = 60  # daily use × 2 months (§2.7)
QUICK_EVAL_SESSIONS = 100  # M0 small eval set / CI quick suite (§12.2, §13 M0 DoD)
DEMO_SEED = 42  # committed demo DB seed (§8.6, §12.2)
QUICK_EVAL_SEED = 4242  # disjoint from history seed (§2.7)

MODES = ("eco", "standard", "turbo")


def _apply_calibration_overrides() -> dict:
    """Overlay calibrated.json (produced by simulator/calibrate.py when the §2.5 gate passes)."""
    path = REPO_ROOT / "data" / "calibration" / "calibrated.json"
    if not path.exists():
        return {}
    overrides = json.loads(path.read_text(encoding="utf-8"))
    applied = {}
    for key, value in overrides.items():
        if key.isupper() and key in globals():
            globals()[key] = value
            applied[key] = value
    return applied


CALIBRATION_OVERRIDES = _apply_calibration_overrides()
