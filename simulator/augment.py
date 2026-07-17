"""Session-plan sampling — the full §2.6 augmentation set.

Axes: start-SoC mix, household mode mix, mid-session mode changes, aging (SoH passed in per
session), a spatial dirt field (per-cell blobs + a habitual dirtier zone), obstacle jitter, and
5 % anomaly sessions (obstacle spike). Map variants / holdout maps are separate hand-authored
seed maps (§2.2) selected by the generator; sensor-noise redraw lives in ``simulator/sensors.py``.

All randomness goes through DetRNG so generated data is reproducible across platforms and numpy
versions (§12.2) — in particular the Poisson(6) obstacle-jitter count is replaced by a
fixed-consumption multiplicative jitter with the same expectation.
"""

import math

from backend.app import config

from .detrng import DetRNG
from .rover import SessionPlan
from .world import MapData, zone_centroid


def _pick_mode(rng: DetRNG) -> str:
    modes = list(config.MODE_MIX)
    return rng.choice_p(modes, [config.MODE_MIX[m] for m in modes])


def _habitual_zone_ids(world: MapData) -> set[int]:
    """The persistently dirtier zones (§2.6 상습 구역): carpets trap dirt, ties broken by area."""
    ranked = sorted(world.zones.values(), key=lambda z: (z.carpet_ratio, z.area_m2), reverse=True)
    return {z.zone_id for z in ranked[: config.HABITUAL_DIRT_ZONES]}


def zone_avg_dirt(world: MapData) -> dict[int, float]:
    """Static per-zone habitual dirt written to the zones table — the predictor's T_req input.

    Deterministic function of the map (no RNG): the habitual zones carry a fixed positive bias,
    everything else sits at the mean. Per-session dirt (below) then varies around this.
    """
    habitual = _habitual_zone_ids(world)
    return {
        zid: config.DIRT_MEAN + (config.HABITUAL_DIRT_BIAS if zid in habitual else 0.0)
        for zid in world.zones
    }


def _blob_boost(world: MapData, rng: DetRNG) -> dict[int, float]:
    """Per-session spatial dirt blobs (§2.6): random hotspots boost the zones nearest them."""
    all_cells = [cell for z in world.zones.values() for cell in z.cells]
    centres = [all_cells[rng.integers(0, len(all_cells))] for _ in range(config.DIRT_BLOB_COUNT)]
    boost: dict[int, float] = {}
    for zid, zone in world.zones.items():
        cx, cy = zone_centroid(zone)
        d = min(math.hypot(cx - bx, cy - by) for bx, by in centres)
        boost[zid] = config.DIRT_BLOB_GAIN * math.exp(-d / config.DIRT_BLOB_RADIUS_CELLS)
    return boost


def sample_plan(
    world: MapData,
    rng: DetRNG,
    allow_mode_change: bool = True,
    soh: float = 1.0,
    allow_anomaly: bool = True,
    start_soc: float | None = None,
) -> SessionPlan:
    mode = _pick_mode(rng)

    if start_soc is None:  # default household mix; eval overrides to probe the full range (§8.1)
        if rng.random() < config.START_SOC_FULL_PROB:
            start_soc = 100.0
        else:
            start_soc = rng.uniform(*config.START_SOC_PARTIAL_RANGE)

    zone_ids = sorted(world.zones)
    if rng.random() >= config.FULL_CLEAN_PROB:
        k = rng.integers(1, min(3, len(zone_ids)) + 1)
        zone_ids = sorted(rng.sample_without_replacement(zone_ids, k))

    avg = zone_avg_dirt(world)
    boost = _blob_boost(world, rng)
    dirt = {
        zid: max(0.0, min(100.0, rng.normal(avg[zid], config.DIRT_SIGMA) + boost[zid]))
        for zid in world.zones
    }

    mode_change = None
    if allow_mode_change and rng.random() < config.MODE_CHANGE_SESSION_PROB:
        other = [m for m in config.MODES if m != mode]
        mode_change = (rng.integers(5, 21), rng.choice(other))

    # Obstacle jitter: session-level multiplicative variation on the base avoidance rate, with an
    # anomaly spike (avoidance ×3) in 5 % of sessions — the "off day" narration demo (§2.6, §8.5).
    jitter = max(0.2, rng.normal(1.0, 0.3))
    avoid_rate = config.OBST_AVOID_PER_MIN * jitter
    anomaly = allow_anomaly and rng.random() < config.ANOMALY_SESSION_PROB
    if anomaly:
        avoid_rate *= config.ANOMALY_AVOID_MULT
    avoid_rate = min(0.95, avoid_rate)

    resume = rng.random() < config.RESUME_PROB

    return SessionPlan(
        mode=mode,
        start_soc=start_soc,
        zone_ids=tuple(zone_ids),
        dirt_by_zone=dirt,
        mode_change=mode_change,
        soh=soh,
        avoid_rate=avoid_rate,
        anomaly=anomaly,
        resume=resume,
    )
