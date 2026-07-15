"""Seed-fixed demo DB generation (SPEC §8.6, §12.2) and canonical determinism hash.

Usage:
  python -m simulator.generate --seed 42 --sessions 60 --out data/demo.db
  python -m simulator.generate --seed 42 --sessions 60 --out /tmp/x.db --verify data/demo.db

The determinism gate compares a *canonical* hash (ordered logical dump), not file bytes,
so it is robust to SQLite version/page-layout differences across machines and CI.
Timestamps derive from a fixed base date — never from the wall clock.
"""

import argparse
import hashlib
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from backend.app import config
from backend.app.db.models import Base
from backend.app.db.session import make_engine

from .augment import sample_plan
from .detrng import DetRNG
from .rover import simulate_session
from .world import MapData, load_map

BASE_STARTED_AT = datetime(2026, 5, 10, 0, 0)  # fixed epoch for reproducibility
SEED_MAP_PATH = config.REPO_ROOT / "data" / "seed_maps" / "base_60m2.json"


def build_db(
    out_path: str | Path,
    seed: int = config.DEMO_SEED,
    n_sessions: int = config.HISTORY_SESSIONS,
    map_path: str | Path = SEED_MAP_PATH,
    allow_mode_change: bool = True,
) -> MapData:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()

    world = load_map(map_path)
    rng = DetRNG(seed)
    engine = make_engine(out_path, read_only=False)
    Base.metadata.create_all(engine)

    with sqlite3.connect(out_path) as con:
        con.executemany(
            "INSERT INTO zones VALUES (?,?,?,?,?)",
            [
                (z.zone_id, z.name, z.area_m2, z.carpet_ratio, config.DIRT_MEAN)
                for z in world.zones.values()
            ],
        )
        con.execute(
            "INSERT INTO grid_maps VALUES (?,?,?)",
            (world.map_id, world.name, json.dumps(world.raw, ensure_ascii=False)),
        )

        for i in range(n_sessions):
            plan = sample_plan(world, rng, allow_mode_change=allow_mode_change)
            sim = simulate_session(world, plan, rng)
            session_id = f"S{seed}-{i:04d}"
            started = BASE_STARTED_AT + timedelta(days=i, hours=8 + rng.integers(0, 12))
            con.execute(
                "INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    session_id,
                    started.isoformat(timespec="minutes"),
                    sim.mode,
                    sim.start_battery,
                    sim.end_battery,
                    sim.duration_min,
                    sim.cleaned_area_m2,
                    sim.travel_dist_m,
                    sim.carpet_ratio,
                    sim.obstacle_hits,
                    sim.dock_returns,
                    sim.mode_changes,
                    sim.soh_at_run,
                    sim.completed,
                    "sim",
                ),
            )
            con.executemany(
                "INSERT INTO ticks VALUES (?,?,?,?,?,?,?,?)",
                [
                    (session_id, t.t_min, t.battery_pct, t.zone_id, t.mode, t.charging, *t.cell)
                    for t in sim.ticks
                ],
            )
        con.commit()
    return world


def _cell(value) -> str:
    # Floats are quantized to 4 decimals so the fingerprint is immune to last-ULP platform
    # noise; every stored float is already rounded to ≤4 decimals, so no information is lost.
    return f"{value:.4f}" if isinstance(value, float) else repr(value)


def canonical_hash(db_path: str | Path) -> str:
    """SHA-256 over an ordered, float-quantized logical dump — stable across SQLite builds,
    numpy versions and CPU platforms (§12.2)."""
    con = sqlite3.connect(db_path)
    h = hashlib.sha256()
    for table, order in (
        ("zones", "zone_id"),
        ("grid_maps", "map_id"),
        ("sessions", "session_id"),
        ("ticks", "session_id, t_min"),
        ("sensor_ticks", "session_id, t_sec"),
        ("next_plan", "plan_id"),
    ):
        h.update(table.encode())
        for row in con.execute(f"SELECT * FROM {table} ORDER BY {order}"):  # noqa: S608
            h.update("|".join(_cell(v) for v in row).encode())
    con.close()
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, default=config.DEMO_SEED)
    ap.add_argument("--sessions", type=int, default=config.HISTORY_SESSIONS)
    ap.add_argument("--out", default=str(config.REPO_ROOT / "data" / "demo.db"))
    ap.add_argument("--no-mode-change", action="store_true", help="disable mid-session changes")
    ap.add_argument("--verify", metavar="DB", help="compare canonical hash against another DB")
    args = ap.parse_args()

    build_db(args.out, args.seed, args.sessions, allow_mode_change=not args.no_mode_change)
    digest = canonical_hash(args.out)
    print(f"built {args.out}: {args.sessions} sessions, canonical sha256 {digest[:16]}…")

    if args.verify:
        other = canonical_hash(args.verify)
        if other != digest:
            print(f"DETERMINISM FAIL: {args.verify} hash {other[:16]}… differs")
            return 1
        print(f"determinism OK: matches {args.verify}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
