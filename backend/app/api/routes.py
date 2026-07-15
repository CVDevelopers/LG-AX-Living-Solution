"""M0 REST endpoints (§6): /api/predict, /api/sessions, /api/simulate, /api/health.

Remaining §6 endpoints arrive with their milestones: /heatmap /plan (M1), /report /explain
(M2+), /llm/proxy (M3), /history /plan-week (M5).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from .. import config
from ..core.predict import predict as core_predict
from ..core.predict.state import CAUTION, SHORTAGE_A, SHORTAGE_B, SUFFICIENT
from ..db import models, repo
from ..db.session import make_session_factory

router = APIRouter(prefix="/api")

_STATES = {SUFFICIENT, CAUTION, SHORTAGE_A, SHORTAGE_B}


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
    return core_predict(battery, mode, zone_list, segments, stats, prev_state)


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
