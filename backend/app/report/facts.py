"""Structured session facts for /report and narration (SPEC §9.5 input contract).

Plain types only — the API layer converts DB rows to these, exactly as ``repo`` does for the
prediction core (§1.1). The narrator and factor decomposition consume ``ReportFacts`` and nothing
else, so every number they emit is traceable to a fact (the §9.4 guardrail).
"""

from dataclasses import dataclass, field

from .. import config


@dataclass(frozen=True)
class ZoneFact:
    zone_id: int
    name: str
    avg_dirt: float


@dataclass(frozen=True)
class ReportFacts:
    session_id: str
    started_at: str
    mode: str
    start_battery: float
    end_battery: float
    dsoc: float  # battery %pt consumed (start − end); contaminated for charged sessions
    duration_min: float
    cleaned_area_m2: float
    carpet_ratio: float
    obstacle_hits: int
    avoid_per_min: float
    dock_returns: int
    mode_changes: int
    completed: int
    charged: bool
    soh_at_run: float
    zones: list[ZoneFact] = field(default_factory=list)
    avg_dirt: float = config.DIRT_MEAN
    high_obstacle: bool = False  # inferred (not a stored flag): avoidance well above typical


def build_facts(
    session: dict,
    cleaned_zone_ids: list[int],
    zones_by_id: dict[int, ZoneFact],
    charged: bool,
) -> ReportFacts:
    """Assemble facts from a session row, its cleaned zone ids, and the zone table (§9.5)."""
    duration = max(session["duration_min"], 1e-9)
    avoid_per_min = session["obstacle_hits"] / duration
    zones = [zones_by_id[z] for z in cleaned_zone_ids if z in zones_by_id]
    avg_dirt = sum(z.avg_dirt for z in zones) / len(zones) if zones else config.DIRT_MEAN
    return ReportFacts(
        session_id=session["session_id"],
        started_at=session["started_at"],
        mode=session["mode"],
        start_battery=session["start_battery"],
        end_battery=session["end_battery"],
        dsoc=round(session["start_battery"] - session["end_battery"], 2),
        duration_min=session["duration_min"],
        cleaned_area_m2=session["cleaned_area_m2"],
        carpet_ratio=session["carpet_ratio"],
        obstacle_hits=session["obstacle_hits"],
        avoid_per_min=round(avoid_per_min, 3),
        dock_returns=session["dock_returns"],
        mode_changes=session["mode_changes"],
        completed=session["completed"],
        charged=charged,
        soh_at_run=session["soh_at_run"],
        zones=zones,
        avg_dirt=round(avg_dirt, 1),
        # An obstacle-spike anomaly (§2.6) is inferred from the log, not read from a stored flag —
        # the narrator sees what a real device sees.
        high_obstacle=avoid_per_min > config.OBST_AVOID_PER_MIN * 2.0,
    )
