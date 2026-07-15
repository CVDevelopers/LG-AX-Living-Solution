"""Rover coverage simulation v0 (SPEC §13 M0): minute-resolution zone-by-zone cleaning.

Produces exactly what a real device would log — sessions and minute ticks (§2.3).
The prediction engine consumes those logs only; nothing here leaks into it (§1 principle 1).
"""

from dataclasses import dataclass, field

from backend.app import config

from .battery import BatteryModel, suction_power_w, travel_power_w
from .detrng import DetRNG
from .world import MapData


@dataclass(frozen=True)
class SessionPlan:
    mode: str
    start_soc: float
    zone_ids: tuple[int, ...]  # visit order
    dirt_by_zone: dict[int, float]
    mode_change: tuple[int, str] | None = None  # (minute, new_mode)
    soh: float = 1.0


@dataclass
class SimTick:
    t_min: int
    battery_pct: float
    zone_id: int | None
    mode: str
    charging: int
    cell: tuple[int, int]


@dataclass
class SimSession:
    mode: str  # starting mode (sessions.mode)
    start_battery: float
    end_battery: float
    duration_min: float
    cleaned_area_m2: float
    travel_dist_m: float
    carpet_ratio: float
    obstacle_hits: int
    dock_returns: int
    mode_changes: int
    soh_at_run: float
    completed: int
    ticks: list[SimTick] = field(default_factory=list)


def simulate_session(world: MapData, plan: SessionPlan, rng: DetRNG) -> SimSession:
    model = BatteryModel(rng, soh=plan.soh)
    # Battery is carried at 3-decimal resolution so the low-battery cutoff (and thus session
    # length) is a stable function of the draw stream, not of last-ULP platform noise (§12.2).
    battery = round(plan.start_soc, 3)
    mode = plan.mode
    t = 0
    cleaned = carpet_cleaned = 0.0
    travel_dist = 0.0
    obstacle_hits = mode_changes = 0
    low_batt = False

    first_zone = world.zones[plan.zone_ids[0]]
    ticks = [SimTick(0, battery, first_zone.zone_id, mode, 0, world.dock)]

    def minute(power_w: float, zone_id: int | None, cell: tuple[int, int]) -> None:
        nonlocal battery, t
        battery = round(max(0.0, battery - model.step_dsoc(power_w)), 3)
        t += 1
        ticks.append(SimTick(t, battery, zone_id, mode, 0, cell))

    for i, zid in enumerate(plan.zone_ids):
        zone = world.zones[zid]
        if i > 0:  # transit between zones (§3.3 travel term)
            travel_dist += config.TRAVEL_M_PER_ZONE
            minute(travel_power_w(), zid, zone.cells[0])
        remaining = zone.area_m2
        while remaining > 0:
            if battery <= config.LOW_BATT_RETURN_PCT:
                low_batt = True
                break
            if plan.mode_change and t == plan.mode_change[0] and mode != plan.mode_change[1]:
                mode = plan.mode_change[1]
                mode_changes += 1
            on_carpet = bool(rng.random() < zone.carpet_ratio)
            # v0: obstacle avoidance as a per-minute Bernoulli event (λ≈0.3) — a stable
            # uniform compare, unlike Poisson's platform-dependent rejection sampling (§12.2).
            avoid = rng.bernoulli(config.OBST_AVOID_PER_MIN) if zone.has_obstacles else 0
            power = suction_power_w(mode, on_carpet, plan.dirt_by_zone[zid], float(avoid))
            speed = config.V_COVER_M2_MIN[mode] * (config.CARPET_SPEED_FACTOR if on_carpet else 1.0)
            area_step = min(speed, remaining)
            cell = zone.cells[rng.integers(0, len(zone.cells))]
            minute(power, zid, cell)
            remaining -= area_step
            cleaned += area_step
            if on_carpet:
                carpet_cleaned += area_step
            obstacle_hits += avoid
        if low_batt:
            break

    dock_returns = 0
    if low_batt:  # abort and head home (§2.6 low-battery return; resume arrives M2)
        travel_dist += config.TRAVEL_M_PER_ZONE
        minute(travel_power_w(), None, world.dock)
        dock_returns = 1

    return SimSession(
        mode=plan.mode,
        start_battery=round(plan.start_soc, 3),
        end_battery=round(battery, 3),
        duration_min=float(t),
        cleaned_area_m2=round(cleaned, 2),
        travel_dist_m=round(travel_dist, 1),
        carpet_ratio=round(carpet_cleaned / cleaned, 4) if cleaned else 0.0,
        obstacle_hits=obstacle_hits,
        dock_returns=dock_returns,
        mode_changes=mode_changes,
        soh_at_run=plan.soh,
        completed=int(not low_batt),
        ticks=ticks,
    )
