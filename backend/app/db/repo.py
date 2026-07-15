"""DB rows → pure-core inputs. The only place ORM types and core types meet (§1.1)."""

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from ..core.predict import Segment, SessionStat, Zone, extract_session_segments
from . import models


def load_zones(db: OrmSession, zone_ids: list[int] | None = None) -> list[Zone]:
    stmt = select(models.Zone).order_by(models.Zone.zone_id)
    if zone_ids:
        stmt = stmt.where(models.Zone.zone_id.in_(zone_ids))
    return [
        Zone(z.zone_id, z.name, z.area_m2, z.carpet_ratio, z.avg_dirt)
        for z in db.scalars(stmt).all()
    ]


def load_history(db: OrmSession) -> tuple[list[Segment], list[SessionStat]]:
    """Sessions newest-first define age 0..n−1 (§3.1); ticks feed segment extraction."""
    sessions = db.scalars(select(models.Session).order_by(models.Session.started_at.desc())).all()
    if not sessions:
        return [], []

    ticks_by_session: dict[str, list] = {s.session_id: [] for s in sessions}
    for t in db.scalars(select(models.Tick)).all():
        if t.session_id in ticks_by_session:
            ticks_by_session[t.session_id].append((t.t_min, t.battery_pct, t.mode, t.charging))

    segments: list[Segment] = []
    stats: list[SessionStat] = []
    for age, s in enumerate(sessions):
        segments.extend(extract_session_segments(ticks_by_session[s.session_id], age))
        stats.append(
            SessionStat(
                age=age,
                mode=s.mode,
                cleaned_area_m2=s.cleaned_area_m2,
                duration_min=s.duration_min,
                carpet_ratio=s.carpet_ratio,
                mode_changes=s.mode_changes,
                dsoc=s.start_battery - s.end_battery,
            )
        )
    return segments, stats
