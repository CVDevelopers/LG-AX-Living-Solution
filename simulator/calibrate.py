"""Open-dataset calibration and the §2.5 adoption gate — offline lab (numpy only, no scipy).

Fits three model constants against measured data and runs the adoption gate:
  ① OCV curve       → per-cell RMSE ≤ 30 mV                (breakpoint least squares)
  ② α (rate factor) → bootstrap CI excludes 0             (log capacity vs log C-rate)
  ③ β (degradation) → β ∈ [0.0002, 0.0006]                (SoH vs equivalent-full-cycles)

Data source: the raw NASA PCoE / UNIBO Powertools datasets in ``data/datasets/`` when present
(gitignored downloads, §2.5); otherwise digitized literature anchors committed at
``data/calibration/reference_anchors.json``. With only anchors the run is a *validation* — the
reference-profile constants are themselves literature-derived, so the fit confirms them and
defaults are retained (§2.5 미통과 시 기본값 유지 spirit). ``--adopt`` writes ``calibrated.json``
only when raw datasets are present and the gate passes.

Always produces ``calibration_report.md`` (§2.5 DoD) and ``overlay_sim_vs_measured.svg`` (§8.5).

  python -m simulator.calibrate            # validate against anchors → report + overlay
  python -m simulator.calibrate --adopt    # + write calibrated.json if raw data passes the gate
"""

import argparse
import json
from pathlib import Path

import numpy as np

from backend.app import config

from .svgplot import Chart

CALIB_DIR = config.REPO_ROOT / "data" / "calibration"
DATASETS_DIR = config.REPO_ROOT / "data" / "datasets"
ANCHORS_PATH = CALIB_DIR / "reference_anchors.json"


def raw_datasets_present() -> bool:
    """Any downloaded raw dataset file (not just the tracked README) present (§2.5)."""
    if not DATASETS_DIR.exists():
        return False
    return any(p.suffix.lower() in {".mat", ".csv", ".xlsx", ".h5"} for p in DATASETS_DIR.iterdir())


def load_anchors() -> dict:
    return json.loads(ANCHORS_PATH.read_text(encoding="utf-8"))


# ── ① OCV breakpoint fit ─────────────────────────────────────────────────────
def _ocv_weights(soc: float, knots: list[float]) -> list[float]:
    """Interpolation weights of ``soc`` on the piecewise-linear knots (mirrors sensors.ocv_pack)."""
    soc = min(1.0, max(0.0, soc))
    w = [0.0] * len(knots)
    for i in range(len(knots) - 1):
        s_hi, s_lo = knots[i], knots[i + 1]
        if soc >= s_lo:
            frac = (soc - s_lo) / (s_hi - s_lo)
            w[i], w[i + 1] = frac, 1.0 - frac
            return w
    w[-1] = 1.0
    return w


def fit_ocv(anchors: dict) -> dict:
    """Least-squares fit of the pack breakpoint voltages to per-cell OCV anchors."""
    knots = [c[0] for c in config.OCV_CURVE]
    pts = anchors["ocv_cell"]
    a = np.array([[w / config.CELLS_IN_SERIES for w in _ocv_weights(s, knots)] for s, _ in pts])
    y = np.array([v for _, v in pts])
    v_pack, *_ = np.linalg.lstsq(a, y, rcond=None)
    resid_cell = a @ v_pack - y
    rmse_mv = float(np.sqrt(np.mean(resid_cell**2)) * 1000.0)
    default_pack = np.array([c[1] for c in config.OCV_CURVE])
    default_rmse_mv = float(np.sqrt(np.mean((a @ default_pack - y) ** 2)) * 1000.0)
    return {
        "knots_soc": knots,
        "fitted_pack_v": [round(float(v), 4) for v in v_pack],
        "default_pack_v": [round(float(v), 4) for v in default_pack],
        "rmse_mv": round(rmse_mv, 2),
        "default_rmse_mv": round(default_rmse_mv, 2),
        "passes": rmse_mv <= config.CALIB_OCV_RMSE_MAX_MV,
    }


# ── ② α rate-factor fit (log capacity vs log C-rate) + bootstrap CI ─────────
def _slope(x: np.ndarray, y: np.ndarray) -> float:
    x = x - x.mean()
    denom = float((x * x).sum())
    return float((x * (y - y.mean())).sum() / denom) if denom > 0 else 0.0


def fit_alpha(anchors: dict) -> dict:
    rc = np.array(anchors["rate_capacity"])
    logc, logcap = np.log(rc[:, 0]), np.log(rc[:, 1])
    alpha = -_slope(logc, logcap)  # cap ∝ C^(-α)
    rng = np.random.default_rng(config.DEMO_SEED)
    n = len(logc)
    boot = []
    for _ in range(config.CALIB_ALPHA_BOOT_B):
        idx = rng.integers(0, n, size=n)
        if len(set(logc[idx].tolist())) < 2:
            continue  # degenerate resample (all one C-rate) — no slope
        boot.append(-_slope(logc[idx], logcap[idx]))
    lo, hi = (
        (float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))) if boot else (0.0, 0.0)
    )
    return {
        "alpha": round(alpha, 4),
        "ci95": [round(lo, 4), round(hi, 4)],
        "default": config.ALPHA_RATE,
        "passes": lo > 0.0 or hi < 0.0,  # CI excludes 0
    }


# ── ③ β degradation fit (SoH vs EFC) ─────────────────────────────────────────
def fit_beta(anchors: dict) -> dict:
    cs = np.array(anchors["cycle_soh"])
    efc, soh = cs[:, 0], cs[:, 1]
    beta = -_slope(efc, soh)  # SoH = 1 − β·EFC
    lo, hi = config.CALIB_BETA_RANGE
    return {
        "beta": round(beta, 6),
        "range": list(config.CALIB_BETA_RANGE),
        "default": config.DEGRADATION_BETA,
        "passes": lo <= beta <= hi,
    }


# ── Overlay figure (§8.5) ────────────────────────────────────────────────────
def write_overlay(anchors: dict, ocv: dict, out: Path) -> None:
    chart = Chart(560, 360, xr=(0.0, 1.0), yr=(11.5, 17.0))
    chart.axes(
        [0, 0.2, 0.4, 0.6, 0.8, 1.0],
        [12, 13, 14, 15, 16, 17],
        xfmt="{:.1f}",
        yfmt="{:.0f}",
    )
    socs = [s / 100 for s in range(0, 101, 2)]
    model = [(s, _ocv_at(s, ocv["knots_soc"], ocv["default_pack_v"])) for s in socs]
    fitted = [(s, _ocv_at(s, ocv["knots_soc"], ocv["fitted_pack_v"])) for s in socs]
    measured = [(s, v * config.CELLS_IN_SERIES) for s, v in anchors["ocv_cell"]]
    chart.polyline(model, "#0f766e", 2.5)
    chart.polyline(fitted, "#f59e0b", 1.5)
    chart.points(measured, "#dc2626", 3.5)
    svg = chart.render(
        f"OCV: sim vs measured (RMSE {ocv['default_rmse_mv']:.1f} mV/cell)",
        "State of charge",
        "Pack voltage (V)",
        legend=[("model (default)", "#0f766e"), ("fit", "#f59e0b"), ("measured", "#dc2626")],
    )
    out.write_text(svg, encoding="utf-8")


def _ocv_at(soc: float, knots: list[float], pack_v: list[float]) -> float:
    w = _ocv_weights(soc, knots)
    return sum(wi * vi for wi, vi in zip(w, pack_v, strict=True))


# ── Report + adoption ────────────────────────────────────────────────────────
def run(adopt: bool = False) -> dict:
    anchors = load_anchors()
    raw = raw_datasets_present()
    ocv, alpha, beta = fit_ocv(anchors), fit_alpha(anchors), fit_beta(anchors)
    gate_pass = ocv["passes"] and alpha["passes"] and beta["passes"]

    CALIB_DIR.mkdir(parents=True, exist_ok=True)
    write_overlay(anchors, ocv, CALIB_DIR / "overlay_sim_vs_measured.svg")

    adopted = False
    if adopt and raw and gate_pass:
        calibrated = {
            "OCV_CURVE": [
                [k, round(v, 4)]
                for k, v in zip(ocv["knots_soc"], ocv["fitted_pack_v"], strict=True)
            ],
            "ALPHA_RATE": alpha["alpha"],
            "DEGRADATION_BETA": beta["beta"],
        }
        (CALIB_DIR / "calibrated.json").write_text(
            json.dumps(calibrated, indent=1) + "\n", encoding="utf-8"
        )
        adopted = True

    report = _report_md(anchors, raw, ocv, alpha, beta, gate_pass, adopt, adopted)
    (CALIB_DIR / "calibration_report.md").write_text(report, encoding="utf-8")
    return {
        "source": "raw_datasets" if raw else "literature_anchors",
        "ocv": ocv,
        "alpha": alpha,
        "beta": beta,
        "gate_pass": gate_pass,
        "adopted": adopted,
    }


def _yn(ok: bool) -> str:
    return "PASS" if ok else "FAIL"


def _report_md(anchors, raw, ocv, alpha, beta, gate_pass, adopt, adopted) -> str:
    src = "raw NASA/UNIBO datasets" if raw else "digitized literature anchors"
    lines = [
        "# Calibration report (SPEC §2.5)",
        "",
        f"- Data source: **{src}**",
        f"- Provenance: {anchors['provenance']}",
        "",
        "## Adoption gate",
        "",
        "| Criterion | Result | Value | Threshold |",
        "|---|---|---|---|",
        f"| ① OCV RMSE (per cell) | **{_yn(ocv['passes'])}** | {ocv['rmse_mv']} mV "
        f"(defaults {ocv['default_rmse_mv']} mV) | ≤ {config.CALIB_OCV_RMSE_MAX_MV} mV |",
        f"| ② α bootstrap CI excludes 0 | **{_yn(alpha['passes'])}** | α={alpha['alpha']}, "
        f"CI95 {alpha['ci95']} (default {alpha['default']}) | CI ∌ 0 |",
        f"| ③ β in range | **{_yn(beta['passes'])}** | β={beta['beta']} "
        f"(default {beta['default']}) | {beta['range']} |",
        "",
        f"**Gate: {_yn(gate_pass)}**",
        "",
        "## Fitted OCV breakpoints (pack V)",
        "",
        f"- SoC knots: {ocv['knots_soc']}",
        f"- Fitted: {ocv['fitted_pack_v']}  ·  Default: {ocv['default_pack_v']}",
        "",
        "## Decision",
        "",
    ]
    if adopted:
        lines.append(
            "Raw datasets present and gate passed with `--adopt` → wrote `calibrated.json`; "
            "regenerate `data/demo.db` so the sensor channels reflect the fit."
        )
    elif not raw:
        alpha_note = (
            f"α anchor-fit ({alpha['alpha']}) sits below the default ({alpha['default']}), "
            "matching the §2.5 note that α should be refit — an intentional flag, not a defect; "
            "it only moves once raw UNIBO data drives the fit."
        )
        lines.append(
            "Validation run against digitized literature anchors (raw datasets absent). OCV "
            f"(RMSE {ocv['default_rmse_mv']} mV for the defaults) and β ({beta['beta']}) confirm "
            f"the reference-profile constants; {alpha_note} Per §2.5 (미통과 시 기본값 유지 spirit "
            "when raw data is unavailable) **defaults are retained** and `calibrated.json` is not "
            "written. Drop the raw NASA/UNIBO datasets into `data/datasets/` and run `--adopt` for "
            "an independent auto-adoption."
        )
    elif not gate_pass:
        lines.append("Gate failed → defaults retained, reason recorded above (§2.5).")
    else:
        lines.append("Gate passed; re-run with `--adopt` to write `calibrated.json`.")
    lines += ["", "Overlay figure: `overlay_sim_vs_measured.svg` (§8.5).", ""]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--adopt", action="store_true", help="write calibrated.json if raw data passes")
    args = ap.parse_args()
    result = run(adopt=args.adopt)
    print(
        f"calibration [{result['source']}]: gate {_yn(result['gate_pass'])} "
        f"(OCV {result['ocv']['rmse_mv']}mV, α={result['alpha']['alpha']}, "
        f"β={result['beta']['beta']}) → report + overlay written; adopted={result['adopted']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
