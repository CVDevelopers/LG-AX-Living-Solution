"""Pure prediction core (SPEC §3) — no FastAPI, no SQLAlchemy, no simulator imports."""

from .engine import RateEngine, RuleEngineV1
from .planner import (
    PlanResult,
    best_subset,
    completion_prob,
    rollout,
    subset_feasible,
    subset_value,
)
from .segments import extract_segments, extract_session_segments
from .service import predict
from .types import Segment, SessionStat, Zone

__all__ = [
    "PlanResult",
    "RateEngine",
    "RuleEngineV1",
    "Segment",
    "SessionStat",
    "Zone",
    "best_subset",
    "completion_prob",
    "extract_segments",
    "extract_session_segments",
    "predict",
    "rollout",
    "subset_feasible",
    "subset_value",
]
