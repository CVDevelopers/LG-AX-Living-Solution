"""Full evaluation — 500 sessions, all §8.1 metrics + hardened slices, reliability diagram,
ablation table (§8.5). Offline lab; heavy, so this is a scheduled job (§12.3), not the PR gate.

Design (§2.7, §8.1):
  • Robustness cohorts — one per SoH slice {1.0,.95,.9,.85,.8}. Each cohort fits a matched-SoH
    history (train maps only, §2.2) and evaluates fresh sessions of the SAME SoH across ALL maps,
    so the holdout maps and the SoH-0.8 slice are honestly separable. This is fair: no estimator
    can predict an aged session from a fresh-fit history without an SoH input (which §3 forbids
    as a predictor), so each cohort's history carries its own aging.
  • Ablation — a SEPARATE ramped-aging history (SoH 1.0→0.8 across its timeline) evaluated at the
    aged end, the one regime where the shared drift (§3.2) can show value over raw/EWMA/shrinkage.

Metrics are reported by start-battery band because |T_est−actual| scales with the battery range
projected (§8.1's ≤2 min target was anchored to ~14-min low-battery sessions — the decision-
relevant regime). MAPE (scale-free rate error) and coverage are the battery-independent headlines.

  python -m eval.eval500                 # full 500 → report + reliability diagram + ablation table
  python -m eval.eval500 --quick         # tiny smoke run (used by the unit test)
"""

import argparse
import json
from dataclasses import dataclass

import numpy as np

from backend.app import config
from backend.app.core.predict import extract_session_segments, predict
from backend.app.core.predict.estimator import fit_estimator
from backend.app.core.predict.types import Segment, SessionStat, Zone
from eval.eval_artifacts import write_ablation_md, write_reliability_svg, write_report_md
from simulator.augment import sample_plan, zone_avg_dirt
from simulator.detrng import DetRNG
from simulator.rover import SimSession, simulate_session
from simulator.world import MapData, load_map

REPORT_JSON = config.REPO_ROOT / "eval" / "report_eval500.json"
REPORT_MD = config.REPO_ROOT / "eval" / "eval_report.md"
RELIABILITY_SVG = config.REPO_ROOT / "eval" / "reliability_diagram.svg"
ABLATION_MD = config.REPO_ROOT / "eval" / "ablation_table.md"

_MAP_DIR = config.REPO_ROOT / "data" / "seed_maps"


def _load(files) -> list[MapData]:
    return [load_map(_MAP_DIR / f) for f in files]


def map_zones(world: MapData) -> dict[int, Zone]:
    avg = zone_avg_dirt(world)
    return {
        zid: Zone(zid, z.name, z.area_m2, z.carpet_ratio, avg[zid])
        for zid, z in world.zones.items()
    }


def _charged(sim: SimSession) -> bool:
    return any(t.charging == 1 for t in sim.ticks)


def _seg_stat(sim: SimSession, age: int) -> tuple[list[Segment], SessionStat]:
    ticks = [(t.t_min, t.battery_pct, t.mode, t.charging) for t in sim.ticks]
    segs = extract_session_segments(ticks, age)
    stat = SessionStat(
        age=age,
        mode=sim.mode,
        cleaned_area_m2=sim.cleaned_area_m2,
        duration_min=sim.duration_min,
        carpet_ratio=sim.carpet_ratio,
        mode_changes=sim.mode_changes,
        dsoc=sim.start_battery - sim.end_battery,
        charged=_charged(sim),
    )
    return segs, stat


def _history(maps: list[MapData], n: int, rng: DetRNG, soh_of_age) -> tuple[list, list]:
    """Simulate n history sessions (age 0 = newest). ``soh_of_age(age)`` sets each SoH."""
    segments: list[Segment] = []
    stats: list[SessionStat] = []
    for age in range(n):
        world = maps[age % len(maps)]
        plan = sample_plan(world, rng, allow_mode_change=True, soh=round(soh_of_age(age), 4))
        sim = simulate_session(world, plan, rng)
        segs, stat = _seg_stat(sim, age)
        segments.extend(segs)
        stats.append(stat)
    return segments, stats


@dataclass
class EvalRec:
    slice_soh: float
    map_id: str
    holdout: bool
    mode: str
    start: float
    completed: int
    mode_change: bool
    anomaly: bool
    charged: bool
    time_err: float
    treq_err: float | None
    ape: float
    covered: int
    p_complete: float
    pred_state: str


def _eval_one(plan, sim: SimSession, world: MapData, holdout: bool, segments, stats) -> EvalRec:
    zones = [map_zones(world)[z] for z in plan.zone_ids]
    out = predict(sim.start_battery, sim.mode, zones, segments, stats)
    dsoc = sim.start_battery - sim.end_battery
    r_actual = dsoc / sim.duration_min if sim.duration_min > 0 else 0.0
    t_actual = (sim.start_battery - config.B_RES_DEFAULT_PCT) / r_actual if r_actual > 0 else 0.0
    time_err = ape = 0.0
    covered = 0
    if out["t_est_min"] > 0 and r_actual > 0:
        r_pred = (sim.start_battery - config.B_RES_DEFAULT_PCT) / out["t_est_min"]
        time_err = abs(out["t_est_min"] - t_actual)
        ape = abs(r_pred * sim.duration_min - dsoc) / dsoc if dsoc > 0 else 0.0
        covered = int(out["t_lo_min"] <= t_actual <= out["t_hi_min"])
    treq_err = abs(out["t_req_min"] - sim.duration_min) if sim.completed else None
    return EvalRec(
        slice_soh=round(plan.soh, 2),
        map_id=world.map_id,
        holdout=holdout,
        mode=sim.mode,
        start=sim.start_battery,
        completed=sim.completed,
        mode_change=sim.mode_changes > 0,
        anomaly=sim.anomaly,
        charged=_charged(sim),
        time_err=time_err,
        treq_err=treq_err,
        ape=ape,
        covered=covered,
        p_complete=out["p_complete"],
        pred_state=out["state"],
    )


# ── Ablation rate estimators (§8.5) ──────────────────────────────────────────
def _ablation_rates(segments: list[Segment]) -> dict[str, dict[str, float]]:
    prior = config.R_PRIOR_PCT_MIN
    fit = fit_estimator(segments)
    raw, ewma = {}, {}
    for m in config.MODES:
        segs = [s for s in segments if s.mode == m]
        if not segs:
            raw[m] = ewma[m] = prior[m]
            continue
        rate = np.array([s.rate for s in segs])
        raw[m] = float(rate.mean())  # unweighted per-mode mean
        age = np.array([s.age for s in segs], dtype=float)
        dt = np.array([s.dt_min for s in segs], dtype=float)
        w = 0.5 ** (age / config.HALFLIFE_BASE_SESSIONS) * (dt / config.SEG_LEN_NORM_MIN)
        ewma[m] = float((w * rate).sum() / w.sum())  # +recency, no shrink/drift
    return {"raw": raw, "+ewma": ewma, "+shrink": dict(fit.base), "+drift": dict(fit.r_tilde)}


def _pct(xs) -> float:
    return round(100.0 * sum(xs) / len(xs), 1) if xs else 0.0


def _mae(xs) -> float:
    return round(sum(xs) / len(xs), 3) if xs else 0.0


def run(per_slice: int = 100, hist_n: int = config.EVAL_HISTORY_SESSIONS) -> dict:
    train_maps = _load(config.TRAIN_MAP_FILES)
    holdout_maps = _load(config.HOLDOUT_MAP_FILES)
    all_maps = train_maps + holdout_maps
    holdout_ids = {m.map_id for m in holdout_maps}
    rng = DetRNG(config.EVAL_SEED)
    lo_soc, hi_soc = config.EVAL_START_SOC_RANGE

    recs: list[EvalRec] = []
    seg_ape = {"clean": [], "mode_change": [], "resume": []}  # §3.1 refinement check (rate MAPE)
    for soh in config.SOH_SLICES:
        # A recent aging trend ending at this cohort's SoH → drift stays active (§3.2), unlike a
        # flat-SoH history where base absorbs the level and drift collapses to 1.
        def trend(age: int, s: float = soh) -> float:
            return min(1.0, s + config.EVAL_AGING_TREND_DELTA * age / max(1, hist_n - 1))

        segments, stats = _history(train_maps, hist_n, rng, trend)
        r_tilde = fit_estimator(segments).r_tilde
        for i in range(per_slice):
            world = all_maps[i % len(all_maps)]
            start = rng.uniform(lo_soc, hi_soc)
            plan = sample_plan(world, rng, allow_mode_change=True, soh=soh, start_soc=start)
            sim = simulate_session(world, plan, rng)
            rec = _eval_one(plan, sim, world, world.map_id in holdout_ids, segments, stats)
            recs.append(rec)
            # Contaminated sessions contribute only clean segments to the fit (§3.1); score those
            # segments' rates against the estimator to prove the refinement works.
            segs, _ = _seg_stat(sim, 0)
            apes = [abs(sg.rate - r_tilde[sg.mode]) / r_tilde[sg.mode] for sg in segs]
            key = "resume" if rec.charged else "mode_change" if rec.mode_change else "clean"
            seg_ape[key].extend(apes)

    metrics = _aggregate(recs, seg_ape)

    # Ablation on a ramped-aging history (SoH 1.0 oldest → 0.8 newest), evaluated at SoH 0.8.
    def ramp(age: int) -> float:
        return 0.8 + 0.2 * (age / max(1, hist_n - 1))

    ab_seg, _ = _history(train_maps, hist_n, rng, ramp)
    ab_rates = _ablation_rates(ab_seg)
    metrics["ablation"] = _ablation(ab_rates, train_maps, per_slice, rng)
    metrics["n_eval"] = len(recs)
    metrics["config"] = {"per_slice": per_slice, "hist_n": hist_n, "eval_seed": config.EVAL_SEED}
    return metrics, recs


def _band_mae(recs, lo, hi) -> dict:
    xs = [r.time_err for r in recs if lo <= r.start < hi]
    return {"n": len(xs), "time_mae": _mae(xs)}


def _aggregate(recs: list[EvalRec], seg_ape: dict) -> dict:
    clean = [r for r in recs if not r.charged and not r.mode_change]  # clean-discharge, one mode
    # Time MAE scales with the battery range projected, so the min-based targets are read on the
    # low-battery DECISION band (where "clean now?" is actually decided); MAPE/coverage/T_req are
    # battery-independent and use all clean sessions.
    dec = [r for r in clean if r.start <= 25.0]
    bands = {
        "0-25": _band_mae(clean, 0, 25),
        "25-50": _band_mae(clean, 25, 50),
        "50-75": _band_mae(clean, 50, 75),
        "75-100": _band_mae(clean, 75, 101),
    }
    treq = [r.treq_err for r in clean if r.treq_err is not None]
    aging_dec = [r.time_err for r in dec if r.slice_soh == min(config.SOH_SLICES)]
    holdout_dec = [r.time_err for r in dec if r.holdout]
    train_dec = [r.time_err for r in dec if not r.holdout]

    def seg_mape(xs):
        return round(100.0 * sum(xs) / len(xs), 2) if xs else 0.0

    return {
        "headline": {
            "time_mae_decision_band_min": _mae([r.time_err for r in dec]),  # start ≤25 %
            "time_mae_overall_min": _mae([r.time_err for r in clean]),
            "treq_mae_min": _mae(treq),
            "mape_pct": seg_mape([r.ape for r in clean]),
            "coverage_pct": _pct([r.covered for r in clean]),
            "state_agreement_pct": _pct(
                [int((r.p_complete >= 0.5) == bool(r.completed)) for r in clean]
            ),
        },
        "targets": {
            "time_mae_min": config.TARGET_TIME_MAE_MIN,
            "treq_mae_min": config.TARGET_TREQ_MAE_MIN,
            "mape_pct": config.TARGET_MAPE_PCT,
            "coverage_range": list(config.TARGET_COVERAGE_RANGE),
            "state_agreement": config.TARGET_STATE_AGREEMENT,
            "aging_mae_min": config.TARGET_AGING_MAE_MIN,
        },
        "time_mae_by_start_band": bands,
        "hardened_slices": {
            "aging_soh_min_mae": {
                "soh": min(config.SOH_SLICES),
                "n": len(aging_dec),
                "time_mae": _mae(aging_dec),
            },
            "holdout_maps_mae": {"n": len(holdout_dec), "time_mae": _mae(holdout_dec)},
            "train_maps_mae": {"n": len(train_dec), "time_mae": _mae(train_dec)},
            "holdout_over_train_ratio": (
                round(_mae(holdout_dec) / _mae(train_dec), 3) if _mae(train_dec) else None
            ),
            "ar1_decision_mae": {"n": len(dec), "time_mae": _mae([r.time_err for r in dec])},
            # Contaminated sessions are refined to clean segments (§3.1); their segment-rate MAPE
            # is comparable to clean segments' → refinement, not corruption.
            "clean_seg_mape": {"n": len(seg_ape["clean"]), "mape_pct": seg_mape(seg_ape["clean"])},
            "mode_change_seg_mape": {
                "n": len(seg_ape["mode_change"]),
                "mape_pct": seg_mape(seg_ape["mode_change"]),
            },
            "resume_seg_mape": {
                "n": len(seg_ape["resume"]),
                "mape_pct": seg_mape(seg_ape["resume"]),
            },
        },
        "reliability": _reliability(clean),
        "counts": {
            "total": len(recs),
            "clean": len(clean),
            "charged": sum(r.charged for r in recs),
            "mode_change": sum(r.mode_change for r in recs),
            "anomaly": sum(r.anomaly for r in recs),
            "holdout": sum(r.holdout for r in recs),
        },
    }


def _reliability(clean: list[EvalRec]) -> dict:
    bins = config.RELIABILITY_BINS
    edges = np.linspace(0.0, 1.0, bins + 1)
    out = []
    for i in range(bins):
        lo, hi = edges[i], edges[i + 1]
        inb = [
            r for r in clean if (lo <= r.p_complete < hi) or (i == bins - 1 and r.p_complete == 1.0)
        ]
        out.append(
            {
                "bin": [round(float(lo), 2), round(float(hi), 2)],
                "center": round(float((lo + hi) / 2), 3),
                "n": len(inb),
                "predicted": round(float(np.mean([r.p_complete for r in inb])), 3) if inb else None,
                "observed": round(float(np.mean([r.completed for r in inb])), 3) if inb else None,
            }
        )
    return out


def _ablation(ab_rates: dict[str, dict[str, float]], maps, per_slice, rng) -> list[dict]:
    sessions = []  # (start, mode, actual r) at SoH 0.8, fixed decision-band start (clean signal)
    for i in range(per_slice):
        world = maps[i % len(maps)]
        plan = sample_plan(
            world,
            rng,
            allow_mode_change=False,
            soh=0.8,
            allow_anomaly=False,
            start_soc=config.ABLATION_START_SOC,
        )
        sim = simulate_session(world, plan, rng)
        if _charged(sim) or sim.duration_min <= 0:
            continue
        r_actual = (sim.start_battery - sim.end_battery) / sim.duration_min
        if r_actual > 0:
            sessions.append((sim.start_battery, sim.mode, r_actual))
    rows = []
    prev = None
    for stage, rates in ab_rates.items():
        errs = []
        for start, mode, r_actual in sessions:
            t_actual = (start - config.B_RES_DEFAULT_PCT) / r_actual
            t_est = (start - config.B_RES_DEFAULT_PCT) / rates[mode]
            errs.append(abs(t_est - t_actual))
        mae = _mae(errs)
        rows.append(
            {
                "stage": stage,
                "time_mae": mae,
                "delta": None if prev is None else round(mae - prev, 3),
            }
        )
        prev = mae
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--quick", action="store_true", help="tiny smoke run")
    args = ap.parse_args()
    per_slice = 6 if args.quick else config.EVAL_SESSIONS // len(config.SOH_SLICES)
    hist_n = 18 if args.quick else config.EVAL_HISTORY_SESSIONS
    metrics, _ = run(per_slice=per_slice, hist_n=hist_n)

    REPORT_JSON.write_text(
        json.dumps(metrics, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    write_reliability_svg(metrics["reliability"], RELIABILITY_SVG)
    write_ablation_md(metrics["ablation"], ABLATION_MD)
    write_report_md(metrics, REPORT_MD)

    h = metrics["headline"]
    print(
        f"eval-500 [{metrics['n_eval']} sessions]: decision-band time MAE "
        f"{h['time_mae_decision_band_min']} min, MAPE {h['mape_pct']} %, coverage "
        f"{h['coverage_pct']} %, state {h['state_agreement_pct']} % → artifacts written"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
