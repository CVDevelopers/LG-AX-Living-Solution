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

# ── Degradation (§2.4d) ──────────────────────────────────────────────────────
# EFC += ΔSoC/100 × w_mode ; SoH = 1 − β·EFC. β chosen so 500 full-equivalent cycles lose
# ≈20 % (12.4–24.1 % band center [R17]) and 300–500 cycles reach SoH 80 % [R3][R6].
DEGRADATION_BETA = 0.0004
EFC_WEIGHT_BY_MODE = {"eco": 1.0, "standard": 1.05, "turbo": 1.2}  # w_mode (§2.4d)
# The demo device is mid-life, not box-fresh: a unit with two months of dense daily history has
# accumulated cycles, so aging drift (§3.2) is real and observable. β·EFC → SoH ≈ 0.96 at t0.
SIM_INITIAL_EFC = 100.0

# ── Voltage/temperature channels (§2.4c) — 4S pack, logged to sensor_ticks (§2.3) ───
CELLS_IN_SERIES = 4  # 4S pack → per-cell OCV = pack/4; calibration RMSE per cell (§2.1, §2.5)
# OCV(SoC) piecewise-linear, 3 regions: initial drop / plateau / knee (pack volts) [R14][R15].
OCV_CURVE = (
    (1.00, 16.8),  # full charge
    (0.85, 15.8),  # end of the initial drop
    (0.15, 14.2),  # end of the plateau — knee onset
    (0.00, 12.0),  # cutoff
)
R_INT_R0_OHM = 0.120  # base pack internal resistance R0 [R15] (§2.4c)
R_INT_SOH_COEF = 1.5  # R_int = R0·(1 + 1.5·(1−SoH))·… aging term [R15][R16]
R_INT_KNEE_COEF = 2.0  # ·(1 + 2·max(0, 0.15−SoC)/0.15) low-SoC internal-resistance rise [R14]
R_INT_KNEE_SOC = 0.15
TEMP_AMB_C = 25.0  # ambient temperature (§2.4c)  [modeling choice]
TEMP_RISE_COEF = 0.012  # dT/dt = P·0.012 − (T−T_amb)/τ ; equilibrium ΔT ≈ P·coef·τ (§2.4c)
TEMP_DECAY_TAU_MIN = 25.0  # thermal decay time constant (minutes)  [modeling choice]
V_NOISE_V = 0.010  # sensor noise ±10 mV (§2.4c)
I_NOISE_FRAC = 0.02  # sensor noise ±2 % of current (§2.4c)
T_NOISE_C = 0.3  # sensor noise ±0.3 °C (§2.4c)
SENSOR_RECENT_SESSIONS = 20  # 1 s raw kept for the most recent N sessions; older → 1 min (§2.3)

# ── Coverage / motion (simulator v0 + T_req inversion) ──────────────────────
V_COVER_M2_MIN = {
    "eco": 0.90,
    "standard": 1.00,
    "turbo": 1.10,
}  # ≈1 m²/min class coverage; 60 m²·std ≈ 60 min → session −45 % ≈ [R13]  [modeling choice]
CARPET_SPEED_FACTOR = 0.8  # slower on carpet [R9] → ≈1.6× energy per m² (§2.4a)
V_TRAVEL_M_MIN = 18.0  # ≈0.3 m/s transit speed  [modeling choice]
ROVER_SWATH_M = 0.25  # brush width; coverage m²/min → linear m/s for the sensor log (§2.4c)
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

# ── Simulator session mix — full augmentation (§2.6) ─────────────────────────
START_SOC_FULL_PROB = 0.6  # {100 %: 0.6, U(50,95): 0.4}
START_SOC_PARTIAL_RANGE = (50.0, 95.0)
MODE_MIX = {"eco": 0.3, "standard": 0.5, "turbo": 0.2}  # household pattern (§2.6)
MODE_CHANGE_SESSION_PROB = 0.10  # one mid-session mode change in 10 % of sessions (§2.6)
DIRT_MEAN, DIRT_SIGMA = 50.0, 20.0  # zone dirt ~ clip(N(50, 20²), 0, 100) (§2.6)
FULL_CLEAN_PROB = 0.5  # half full cleans, half partial zone subsets  [modeling choice]
# Dirt field = per-cell blobs + a habitual (persistently dirtier) zone bias (§2.6).
DIRT_BLOB_COUNT = 3  # habitual-dirt hotspots per session  [modeling choice]
DIRT_BLOB_GAIN = 30.0  # extra dirt at a blob centre, decaying with distance (§2.6)
DIRT_BLOB_RADIUS_CELLS = 3.0
HABITUAL_DIRT_ZONES = 1  # zones carrying a persistent higher-dirt bias (§2.6 상습 구역)
HABITUAL_DIRT_BIAS = 15.0
# Aging-stage slices for eval robustness (§2.6 노화 단계, §8.1 노화 강건성).
SOH_SLICES = (1.0, 0.95, 0.9, 0.85, 0.8)
# Obstacle jitter: Poisson(6) is banned cross-platform (§12.2) — surrogate is a fixed-consumption
# sum of Bernoullis (mean OBSTACLE_JITTER_MEAN, same expectation) via DetRNG.
OBSTACLE_JITTER_MEAN = 6
# Anomaly sessions: obstacle spike (avoidance ×3) — the "off day" narration demo (§2.6, §8.5).
ANOMALY_SESSION_PROB = 0.05
ANOMALY_AVOID_MULT = 3.0
# Interruption + resume (§2.6 저잔량 도크 복귀·재개 [R3]): a fraction of low-battery returns dock,
# charge, then resume the leftover zones — producing charge-resume sessions (dock_returns>0) that
# segment extraction (§3.1) must refine, not discard.
RESUME_PROB = 0.5
RESUME_CHARGE_MARGIN_PCT = 12.0  # charge to (reserve + estimated need + margin) then resume

# ── Data set sizing (§2.7) ───────────────────────────────────────────────────
HISTORY_SESSIONS = 60  # daily use × 2 months (§2.7)
QUICK_EVAL_SESSIONS = 100  # M0 small eval set / CI quick suite (§12.2, §13 M0 DoD)
DEMO_SEED = 42  # committed demo DB seed (§8.6, §12.2)
QUICK_EVAL_SEED = 4242  # disjoint from history seed (§2.7)
EVAL_SESSIONS = 500  # full eval — holdout maps + SoH slices + hardened slices (§8.1, §2.7)
EVAL_SEED = 500042  # disjoint from history (42) and quick-eval (4242) seeds (§2.7)
EVAL_HISTORY_SESSIONS = 60  # matched-SoH history fitted per cohort (§2.7)
RELIABILITY_BINS = 10  # reliability-diagram bins (§8.5)
# Eval probes the FULL operating range incl. the low-battery decision regime; the ≤2-min time
# target (§8.1) was anchored to ~14-min low-battery sessions, so that is the reported band.
EVAL_START_SOC_RANGE = (12.0, 100.0)
# A cohort's history ages by this much over its recent window, ending at the slice SoH — a real
# recent aging trend so base (half-life 40) lags and the shared drift (§3.2) stays active and
# propagates aging to sparse modes, exactly as in deployment.
EVAL_AGING_TREND_DELTA = 0.03
ABLATION_START_SOC = (
    35.0  # fixed decision-band start → clean, amplification-free ablation signal (§8.5)
)

# ── §8.1 evaluation targets (eval report scores pass/fail against these) ─────
TARGET_TIME_MAE_MIN = 2.0
TARGET_TREQ_MAE_MIN = 2.0
TARGET_MAPE_PCT = 12.0
TARGET_COVERAGE_RANGE = (86.0, 94.0)
TARGET_STATE_AGREEMENT = 0.90
TARGET_AGING_MAE_MIN = 2.5  # SoH 0.8 slice (§8.1 노화 강건성)
TARGET_SHAP_SIGN = 0.95  # SHAP/factor sign consistency (§3.6, §8.1)

# ── Seed maps (§2.2: base + 2 variants [train] + 2 holdout [eval-only]) ──────
TRAIN_MAP_FILES = ("base_60m2.json", "var_split.json", "var_open.json")
HOLDOUT_MAP_FILES = ("holdout_studio.json", "holdout_hall.json")

# ── Calibration adoption gate (§2.5) ─────────────────────────────────────────
CALIB_OCV_RMSE_MAX_MV = 30.0  # ① OCV RMSE ≤ 30 mV/cell
CALIB_BETA_RANGE = (0.0002, 0.0006)  # ③ β ∈ [0.0002, 0.0006]
CALIB_ALPHA_BOOT_B = 1000  # ② bootstrap reps for the α CI (must exclude 0)

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
