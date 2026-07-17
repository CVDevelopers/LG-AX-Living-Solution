"""Rover coverage simulation (SPEC §2.4, §2.6): minute-resolution zone-by-zone cleaning.

Produces exactly what a real device would log — sessions and minute ticks (§2.3) — plus, kept
in memory for the sensor layer (§2.4c), a per-minute load trace and the session's EFC increment
(§2.4d). The prediction engine consumes the logged ticks only; nothing here leaks into it
(§1 principle 1).

Session shapes covered (§2.6): partial/full cleans, mid-session mode changes, anomaly sessions
(obstacle spike), and low-battery dock-return with optional charge-and-resume (dock_returns>0),
whose charging interval segment extraction (§3.1) refines away.
"""

from dataclasses import dataclass, field

from backend.app import config

from .battery import BatteryModel, efc_increment, suction_power_w, travel_power_w
from .detrng import DetRNG
from .sensors import MinuteState
from .world import MapData

_TRAVEL_WHEEL_MPS = config.V_TRAVEL_M_MIN / 60.0


@dataclass(frozen=True)
class SessionPlan:
    mode: str
    start_soc: float
    zone_ids: tuple[int, ...]  # visit order
    dirt_by_zone: dict[int, float]
    mode_change: tuple[int, str] | None = None  # (minute, new_mode)
    soh: float = 1.0
    avoid_rate: float = (
        config.OBST_AVOID_PER_MIN
    )  # per-minute avoidance prob (jitter/anomaly folded in)
    anomaly: bool = False  # obstacle-spike session, flagged for the "off day" demo (§2.6, §8.5)
    resume: bool = True  # charge-and-resume after a low-battery dock return (§2.6)


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
    anomaly: bool = False
    efc_delta: float = 0.0  # equivalent full cycles consumed this session (§2.4d)
    ticks: list[SimTick] = field(default_factory=list)
    minute_states: list[MinuteState] = field(default_factory=list)  # for the sensor layer (§2.4c)


def _clean_wheel_mps(mode: str, on_carpet: bool) -> float:
    speed = config.V_COVER_M2_MIN[mode] * (config.CARPET_SPEED_FACTOR if on_carpet else 1.0)
    return speed / config.ROVER_SWATH_M / 60.0


def simulate_session(world: MapData, plan: SessionPlan, rng: DetRNG) -> SimSession:
    model = BatteryModel(rng, soh=plan.soh)
    # Battery is carried at 3-decimal resolution so the low-battery cutoff (and thus session
    # length) is a stable function of the draw stream, not of last-ULP platform noise (§12.2).
    battery = round(plan.start_soc, 3)
    mode = plan.mode
    t = 0
    cleaned = carpet_cleaned = 0.0
    travel_dist = 0.0
    obstacle_hits = mode_changes = dock_returns = 0
    efc_delta = 0.0

    first_zone = world.zones[plan.zone_ids[0]]
    ticks = [SimTick(0, battery, first_zone.zone_id, mode, 0, world.dock)]
    minute_states: list[MinuteState] = []

    def minute(
        power_w: float,
        zone_id: int | None,
        cell: tuple[int, int],
        wheel_mps: float,
        *,
        charging: bool = False,
        event: str | None = None,
    ) -> None:
        nonlocal battery, t, efc_delta
        soc_start = battery
        if charging:
            battery = round(min(100.0, battery + config.CHARGE_RATE_PCT_MIN), 3)
        else:
            dsoc = model.step_dsoc(power_w)
            battery = round(max(0.0, battery - dsoc), 3)
            efc_delta += efc_increment(dsoc, mode)
        t += 1
        ticks.append(SimTick(t, battery, zone_id, mode, int(charging), cell))
        minute_states.append(
            MinuteState(
                power_w=power_w,
                soc_start=soc_start,
                soc_end=battery,
                mode=mode,
                wheel_speed_mps=wheel_mps,
                charging=charging,
                event=event,
            )
        )

    # Work queue: (zone_id, remaining_area). Lets a resumed session pick up mid-zone (§2.6).
    queue: list[list] = [[zid, world.zones[zid].area_m2] for zid in plan.zone_ids]
    resumed = False

    def clean_queue() -> bool:
        """Clean down the queue; return True if it aborted on low battery."""
        nonlocal battery, mode, cleaned, carpet_cleaned, travel_dist, obstacle_hits, mode_changes
        for i, item in enumerate(queue):
            zid, _ = item
            zone = world.zones[zid]
            if i > 0 or resumed:  # transit into this zone (§3.3 travel term)
                travel_dist += config.TRAVEL_M_PER_ZONE
                minute(travel_power_w(), zid, zone.cells[0], _TRAVEL_WHEEL_MPS)
            while item[1] > 0:
                if battery <= config.LOW_BATT_RETURN_PCT:
                    return True
                if plan.mode_change and t == plan.mode_change[0] and mode != plan.mode_change[1]:
                    mode = plan.mode_change[1]
                    mode_changes += 1
                on_carpet = bool(rng.random() < zone.carpet_ratio)
                avoid = rng.bernoulli(plan.avoid_rate) if zone.has_obstacles else 0
                power = suction_power_w(mode, on_carpet, plan.dirt_by_zone[zid], float(avoid))
                speed = config.V_COVER_M2_MIN[mode] * (
                    config.CARPET_SPEED_FACTOR if on_carpet else 1.0
                )
                area_step = min(speed, item[1])
                cell = zone.cells[rng.integers(0, len(zone.cells))]
                minute(power, zid, cell, _clean_wheel_mps(mode, on_carpet))
                item[1] -= area_step
                cleaned += area_step
                if on_carpet:
                    carpet_cleaned += area_step
                obstacle_hits += avoid
        return False

    low_batt = clean_queue()

    # Low-battery dock return, then optionally charge and resume the leftover work (§2.6 재개 [R3]).
    if low_batt:
        travel_dist += config.TRAVEL_M_PER_ZONE
        minute(travel_power_w(), None, world.dock, _TRAVEL_WHEEL_MPS, event="dock_return")
        dock_returns = 1
        queue = [item for item in queue if item[1] > 0]
        rate_per_area = (
            (plan.start_soc - battery) / cleaned if cleaned > 0 else config.R_PRIOR_PCT_MIN[mode]
        )
        remaining_area = sum(item[1] for item in queue)
        need = remaining_area * rate_per_area
        target = min(100.0, config.LOW_BATT_RETURN_PCT + need + config.RESUME_CHARGE_MARGIN_PCT)
        if plan.resume and queue and target > battery:
            while battery < target:
                minute(0.0, None, world.dock, 0.0, charging=True, event="charging")
            resumed = True
            if clean_queue():  # a second low-battery hit ends the session for good — no re-resume
                travel_dist += config.TRAVEL_M_PER_ZONE
                minute(travel_power_w(), None, world.dock, _TRAVEL_WHEEL_MPS, event="dock_return")
                dock_returns = 2

    completed = int(all(item[1] <= 1e-9 for item in queue))
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
        completed=completed,
        anomaly=plan.anomaly,
        efc_delta=round(efc_delta, 6),
        ticks=ticks,
        minute_states=minute_states,
    )
