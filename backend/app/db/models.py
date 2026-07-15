"""SQLAlchemy models for the §2.3 schema.

`grid_maps` appears in the §1 architecture diagram but not in the §2.3 DDL; resolved here
(M0 decision) as persisted seed-map grids so the DB is self-contained for heatmap/SimView.
`sensor_ticks` exists but stays empty until M2 (sensor channels are out of M0 scope).
"""

from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Zone(Base):
    __tablename__ = "zones"

    zone_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    area_m2: Mapped[float]
    carpet_ratio: Mapped[float] = mapped_column(default=0.0)
    avg_dirt: Mapped[float] = mapped_column(default=50.0)


class Session(Base):
    __tablename__ = "sessions"
    __table_args__ = (CheckConstraint("mode IN ('eco','standard','turbo')", name="mode_check"),)

    session_id: Mapped[str] = mapped_column(primary_key=True)
    started_at: Mapped[str]
    mode: Mapped[str]
    start_battery: Mapped[float]
    end_battery: Mapped[float]
    duration_min: Mapped[float]
    cleaned_area_m2: Mapped[float]
    travel_dist_m: Mapped[float]
    carpet_ratio: Mapped[float]
    obstacle_hits: Mapped[int] = mapped_column(default=0)
    dock_returns: Mapped[int] = mapped_column(default=0)
    mode_changes: Mapped[int] = mapped_column(default=0)  # mid-run changes → segment split (§3.1)
    soh_at_run: Mapped[float] = mapped_column(default=1.0)  # sim metadata, never a predictor input
    completed: Mapped[int]
    source: Mapped[str] = mapped_column(default="sim")


class Tick(Base):
    __tablename__ = "ticks"

    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.session_id"), primary_key=True)
    t_min: Mapped[int] = mapped_column(primary_key=True)
    battery_pct: Mapped[float]
    zone_id: Mapped[int | None] = mapped_column(nullable=True)
    mode: Mapped[str]
    charging: Mapped[int] = mapped_column(default=0)
    cell_x: Mapped[int | None] = mapped_column(nullable=True)
    cell_y: Mapped[int | None] = mapped_column(nullable=True)


class SensorTick(Base):
    __tablename__ = "sensor_ticks"

    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.session_id"), primary_key=True)
    t_sec: Mapped[int] = mapped_column(primary_key=True)
    voltage_v: Mapped[float | None] = mapped_column(nullable=True)
    current_a: Mapped[float | None] = mapped_column(nullable=True)
    temp_c: Mapped[float | None] = mapped_column(nullable=True)
    motor_pwm: Mapped[float | None] = mapped_column(nullable=True)
    wheel_speed_mps: Mapped[float | None] = mapped_column(nullable=True)
    event: Mapped[str | None] = mapped_column(nullable=True)


class NextPlan(Base):
    __tablename__ = "next_plan"

    plan_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[str]
    zones_csv: Mapped[str]
    mode: Mapped[str]
    reason: Mapped[str | None] = mapped_column(nullable=True)
    consumed: Mapped[int] = mapped_column(default=0)


class GridMap(Base):
    __tablename__ = "grid_maps"

    map_id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    cells_json: Mapped[str]  # raw seed-map JSON (§2.2 schema)
