"""quick-100 evaluation (§13 M0 DoD, §12.2 CI regression gate).

Fits the engine on the committed 60-session demo history, then scores it against 100 fresh
eval sessions (seed 4242, disjoint from history per §2.7; no mid-session mode changes so
actuals attribute cleanly to one mode).

  python -m eval.quick100                      # print metrics + write eval/report_quick100.json
  python -m eval.quick100 --write-baseline     # refresh committed baseline (intentional only)
  python -m eval.quick100 --check              # CI gate: time MAE ≤ baseline × 1.10

Metrics:
  time_mae   — |T_est − T_actual|, T_actual = (start − B_res)/r_actual (rate-derived, §8.1)
  treq_mae   — |T_req − actual duration| on completed sessions (§8.1 "반대변 검증")
  mape_pct   — battery-consumption MAPE over the session duration
  coverage   — share of T_actual inside the 90 % interval [t_lo, t_hi] (target 86–94)
"""

import argparse
import json
import sqlite3
import tempfile
from pathlib import Path

from backend.app import config
from backend.app.core.predict import predict
from backend.app.db import repo
from backend.app.db.session import make_session_factory
from simulator.generate import build_db

REPORT_PATH = config.REPO_ROOT / "eval" / "report_quick100.json"
BASELINE_PATH = config.REPO_ROOT / "eval" / "baseline_quick100.json"


def _eval_sessions(db_path: Path) -> list[dict]:
    con = sqlite3.connect(db_path)
    sessions = [
        dict(
            zip(
                ("session_id", "mode", "start", "end", "duration", "completed"),
                row,
                strict=True,
            )
        )
        for row in con.execute(
            "SELECT session_id, mode, start_battery, end_battery, duration_min, completed"
            " FROM sessions ORDER BY session_id"
        )
    ]
    for s in sessions:
        zone_rows = con.execute(
            "SELECT DISTINCT zone_id FROM ticks WHERE session_id=? AND zone_id IS NOT NULL",
            (s["session_id"],),
        ).fetchall()
        s["zones"] = sorted(z for (z,) in zone_rows)
        # Charge-resume sessions have a charging interval → their session-level rate and duration
        # are contaminated (§3.1); they are scored as a hardened slice by eval-500, not here.
        (charged,) = con.execute(
            "SELECT COUNT(*) FROM ticks WHERE session_id=? AND charging=1", (s["session_id"],)
        ).fetchone()
        s["charged"] = charged > 0
    con.close()
    return sessions


def run(history_db: Path = None, n_eval: int = config.QUICK_EVAL_SESSIONS) -> dict:
    history_db = Path(history_db or config.DB_PATH)
    db = make_session_factory(history_db)()
    all_zones = {z.zone_id: z for z in repo.load_zones(db)}
    segments, stats = repo.load_history(db)
    db.close()

    with tempfile.TemporaryDirectory() as tmp:
        eval_db = Path(tmp) / "eval.db"
        build_db(
            eval_db,
            seed=config.QUICK_EVAL_SEED,
            n_sessions=n_eval,
            allow_mode_change=False,
            with_sensors=False,  # quick suite reads sessions/ticks only
        )
        sessions = _eval_sessions(eval_db)

    time_err, treq_err, ape, covered = [], [], [], 0
    scored = [s for s in sessions if not s["charged"]]  # clean-discharge sessions only (§3.1)
    for s in scored:
        zones = [all_zones[z] for z in s["zones"]]
        out = predict(s["start"], s["mode"], zones, segments, stats)
        r_actual = (s["start"] - s["end"]) / s["duration"]
        t_actual = (s["start"] - config.B_RES_DEFAULT_PCT) / r_actual
        if out["t_est_min"] > 0:
            r_pred = (s["start"] - config.B_RES_DEFAULT_PCT) / out["t_est_min"]
            time_err.append(abs(out["t_est_min"] - t_actual))
            ape.append(
                abs(r_pred * s["duration"] - (s["start"] - s["end"])) / (s["start"] - s["end"])
            )
            covered += int(out["t_lo_min"] <= t_actual <= out["t_hi_min"])
        if s["completed"]:
            treq_err.append(abs(out["t_req_min"] - s["duration"]))

    n = len(time_err)
    return {
        "n_eval": len(sessions),
        "n_scored": n,
        "n_completed": len(treq_err),
        "time_mae_min": round(sum(time_err) / n, 3),
        "treq_mae_min": round(sum(treq_err) / len(treq_err), 3),
        "mape_pct": round(100 * sum(ape) / n, 2),
        "coverage_pct": round(100 * covered / n, 1),
        "history_sessions": len(stats),
        "segments_used": len(segments),
        "eval_seed": config.QUICK_EVAL_SEED,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--check", action="store_true", help="fail if time MAE worsens >10% vs baseline"
    )
    ap.add_argument("--write-baseline", action="store_true")
    args = ap.parse_args()

    report = run()
    REPORT_PATH.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    for k, v in report.items():
        print(f"{k:>18}: {v}")

    if args.write_baseline:
        BASELINE_PATH.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
        print(f"baseline written → {BASELINE_PATH}")
    if args.check:
        baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
        limit = baseline["time_mae_min"] * 1.10
        if report["time_mae_min"] > limit:
            print(f"REGRESSION: time MAE {report['time_mae_min']} > {limit:.3f} (baseline×1.10)")
            return 1
        print(f"regression gate OK: {report['time_mae_min']} ≤ {limit:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
