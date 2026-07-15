"""M0–M1 REST endpoints (§6): /api/predict /heatmap /plan /next-plan /sessions /simulate /health.

Remaining §6 endpoints arrive with their milestones: /report /explain (M2+), /llm/proxy (M3),
/history /plan-week (M5).
"""

from datetime import UTC, datetime
from typing import Annotated

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from .. import config
from ..core.predict import predict as core_predict
from ..core.predict.engine import RuleEngineV1
from ..core.predict.state import CAUTION, SHORTAGE_A, SHORTAGE_B, SUFFICIENT
from ..db import models, repo
from ..db.session import make_session_factory
from . import spatial

router = APIRouter(prefix="/api")

_STATES = {SUFFICIENT, CAUTION, SHORTAGE_A, SHORTAGE_B}


def _draws(segments, stats):
    """Fixed-seed joint draws (§3.2) — the single distribution every M1 view shares."""
    engine = RuleEngineV1(segments, stats)
    return engine.joint_draws(np.random.default_rng(config.PREDICT_SEED))


class _Db:
    """Session factory holder — recreated after /api/simulate rebuilds the DB file."""

    factory = None

    @classmethod
    def get(cls):
        if cls.factory is None:
            cls.factory = make_session_factory()
        return cls.factory

    @classmethod
    def reset(cls):
        if cls.factory is not None:
            cls.factory.kw["bind"].dispose()
        cls.factory = None


def get_db():
    db = _Db.get()()
    try:
        yield db
    finally:
        db.close()


DbDep = Annotated[OrmSession, Depends(get_db)]


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "engine": "rule_v1", "db": config.DB_PATH.exists()}


@router.get("/predict")
def predict(
    db: DbDep,
    battery: float = Query(..., ge=0.0, le=100.0),
    mode: str = Query("standard"),
    zones: str | None = Query(None, description="comma-separated zone ids; default all"),
    prev_state: str | None = Query(None),
) -> dict:
    if mode not in config.MODES:
        raise HTTPException(400, f"mode must be one of {config.MODES}")
    if prev_state is not None and prev_state not in _STATES:
        raise HTTPException(400, f"prev_state must be one of {sorted(_STATES)}")

    zone_ids = None
    if zones:
        try:
            zone_ids = [int(z) for z in zones.split(",") if z.strip()]
        except ValueError as err:
            raise HTTPException(400, "zones must be comma-separated integers") from err

    zone_list = repo.load_zones(db, zone_ids)
    if zone_ids and len(zone_list) != len(set(zone_ids)):
        raise HTTPException(400, "unknown zone id in zones")
    if not zone_list:
        raise HTTPException(500, "no zones in DB — run `make db` (or POST /api/simulate)")

    segments, stats = repo.load_history(db)
    # Dynamic reserve (§3.2) from the map, shared with /heatmap and /plan so all three agree
    # on B_res (§1 principle 7). Falls back to the static reserve if no map is stored.
    b_res = None
    try:
        world = repo.load_map(db)
        b_res = spatial.dynamic_b_res(world, list(world.zones), _draws(segments, stats))
    except LookupError:
        pass
    return core_predict(battery, mode, zone_list, segments, stats, prev_state, b_res=b_res)


@router.get("/heatmap")
def heatmap(
    db: DbDep,
    battery: float = Query(..., ge=0.0, le=100.0),
    mode: str = Query("standard"),
) -> dict:
    """§5.2 trajectory heatmap — per-cell completion probability on the shared distribution."""
    if mode not in config.MODES:
        raise HTTPException(400, f"mode must be one of {config.MODES}")
    zones_by_id = {z.zone_id: z for z in repo.load_zones(db)}
    if not zones_by_id:
        raise HTTPException(500, "no zones in DB — run `make db` (or POST /api/simulate)")
    try:
        world = repo.load_map(db)
    except LookupError as err:
        raise HTTPException(500, str(err)) from err

    segments, stats = repo.load_history(db)
    draws = _draws(segments, stats)
    b_res = spatial.dynamic_b_res(world, list(world.zones), draws)
    return spatial.build_heatmap(world, zones_by_id, battery, mode, draws, b_res)


class PlanBody(BaseModel):
    battery: float
    zones: list[int] | None = None  # subset universe to search within; default = all zones


@router.post("/plan")
def plan(db: DbDep, body: PlanBody) -> dict:
    """§5.1 subset planner — the max-value zone set that still completes at ≥ 0.90 (부족A)."""
    if not 0.0 <= body.battery <= 100.0:
        raise HTTPException(400, "battery must be in [0, 100]")
    zones_by_id = {z.zone_id: z for z in repo.load_zones(db, body.zones)}
    if body.zones and set(body.zones) - set(zones_by_id):
        raise HTTPException(400, "unknown zone id in zones")
    if not zones_by_id:
        raise HTTPException(500, "no zones in DB — run `make db` (or POST /api/simulate)")
    try:
        world = repo.load_map(db)
    except LookupError as err:
        raise HTTPException(500, str(err)) from err

    segments, stats = repo.load_history(db)
    draws = _draws(segments, stats)
    b_res = spatial.dynamic_b_res(world, list(world.zones), draws)
    result = spatial.build_plan(world, zones_by_id, body.battery, draws, b_res)
    # None → no subset completes → 부족B (charge first); the client shows the charge banner.
    return {"feasible": result is not None, "plan": result, "b_res": round(b_res, 2)}


class NextPlanBody(BaseModel):
    zone_ids: list[int]
    mode: str
    reason: str | None = None


@router.get("/next-plan")
def get_next_plan(db: DbDep) -> dict:
    """Latest un-consumed carryover plan (§4.2). Profile W uses client storage instead (§12.1)."""
    row = db.scalars(
        select(models.NextPlan)
        .where(models.NextPlan.consumed == 0)
        .order_by(models.NextPlan.plan_id.desc())
    ).first()
    if row is None:
        return {"next_plan": None}
    return {
        "next_plan": {
            "plan_id": row.plan_id,
            "created_at": row.created_at,
            "zone_ids": [int(z) for z in row.zones_csv.split(",") if z],
            "mode": row.mode,
            "reason": row.reason,
        }
    }


@router.post("/next-plan")
def create_next_plan(db: DbDep, body: NextPlanBody) -> dict:
    """Defer the un-selected zones for next visit (§4.2 이월). Disabled on profile W (§12.1)."""
    if config.IS_VERCEL:
        raise HTTPException(403, "next-plan is client-side on this deployment (§12.1)")
    if body.mode not in config.MODES:
        raise HTTPException(400, f"mode must be one of {config.MODES}")
    row = models.NextPlan(
        created_at=datetime.now(UTC).isoformat(timespec="seconds"),
        zones_csv=",".join(str(z) for z in body.zone_ids),
        mode=body.mode,
        reason=body.reason,
        consumed=0,
    )
    db.add(row)
    db.commit()
    return {"ok": True, "plan_id": row.plan_id}


@router.post("/next-plan/{plan_id}/consume")
def consume_next_plan(db: DbDep, plan_id: int) -> dict:
    if config.IS_VERCEL:
        raise HTTPException(403, "next-plan is client-side on this deployment (§12.1)")
    row = db.get(models.NextPlan, plan_id)
    if row is None:
        raise HTTPException(404, "no such plan")
    row.consumed = 1
    db.commit()
    return {"ok": True}


@router.get("/sessions")
def sessions(db: DbDep) -> list[dict]:
    rows = db.scalars(select(models.Session).order_by(models.Session.started_at.desc())).all()
    return [
        {
            "session_id": s.session_id,
            "started_at": s.started_at,
            "mode": s.mode,
            "start_battery": s.start_battery,
            "end_battery": s.end_battery,
            "duration_min": s.duration_min,
            "cleaned_area_m2": s.cleaned_area_m2,
            "mode_changes": s.mode_changes,
            "completed": s.completed,
        }
        for s in rows
    ]


class SimulateBody(BaseModel):
    seed: int = config.DEMO_SEED
    sessions: int = config.HISTORY_SESSIONS


@router.post("/simulate")
def simulate(body: SimulateBody) -> dict:
    if config.IS_VERCEL:
        # Profile W ships a read-only seed bundle; public URLs must not mutate it (§12.1).
        raise HTTPException(403, "simulate is disabled on this deployment")
    from simulator.generate import build_db, canonical_hash  # offline lab, imported lazily

    build_db(config.DB_PATH, seed=body.seed, n_sessions=body.sessions)
    _Db.reset()
    return {"ok": True, "sessions": body.sessions, "hash": canonical_hash(config.DB_PATH)}
