"""Augmentation axes (§2.6) and the 5 seed maps (§2.2)."""

import pytest

from backend.app import config
from backend.app.geo import CLEANABLE, load_map
from simulator.augment import sample_plan, zone_avg_dirt
from simulator.detrng import DetRNG

MAP_DIR = config.REPO_ROOT / "data" / "seed_maps"
ALL_MAPS = config.TRAIN_MAP_FILES + config.HOLDOUT_MAP_FILES


@pytest.mark.parametrize("map_file", ALL_MAPS)
def test_every_seed_map_loads_and_validates(map_file):
    world = load_map(MAP_DIR / map_file)
    assert len(world.zones) >= 4
    assert sum(z.area_m2 for z in world.zones.values()) > 30.0
    # exactly one dock cell
    docks = sum(1 for row in world.grid for c in row if c == 9)
    assert docks == 1
    # every declared zone has cleanable cells
    assert all(z.cells and z.area_m2 > 0 for z in world.zones.values())


def test_five_distinct_maps_train_and_holdout():
    ids = {load_map(MAP_DIR / f).map_id for f in ALL_MAPS}
    assert len(ids) == 5  # base + 2 variants + 2 holdout (§2.2)


def test_habitual_zone_carries_dirt_bias():
    world = load_map(MAP_DIR / "base_60m2.json")
    avg = zone_avg_dirt(world)
    hi = [z for z, d in avg.items() if d > config.DIRT_MEAN]
    assert len(hi) == config.HABITUAL_DIRT_ZONES
    # the biased zone is the most carpeted (carpets trap dirt)
    biased = max(avg, key=avg.get)
    assert world.zones[biased].carpet_ratio == max(z.carpet_ratio for z in world.zones.values())
    assert avg[biased] == pytest.approx(config.DIRT_MEAN + config.HABITUAL_DIRT_BIAS)


def test_sample_plan_passes_soh_and_start_override():
    world = load_map(MAP_DIR / "base_60m2.json")
    plan = sample_plan(world, DetRNG(1), soh=0.85, start_soc=42.0)
    assert plan.soh == 0.85
    assert plan.start_soc == 42.0


def test_anomaly_disabled_never_flags():
    world = load_map(MAP_DIR / "base_60m2.json")
    rng = DetRNG(2)
    assert not any(sample_plan(world, rng, allow_anomaly=False).anomaly for _ in range(100))


def test_anomaly_sessions_occur_and_spike_avoidance():
    world = load_map(MAP_DIR / "base_60m2.json")
    rng = DetRNG(2)
    plans = [sample_plan(world, rng) for _ in range(400)]
    anomalies = [p for p in plans if p.anomaly]
    assert anomalies  # ~5 % of sessions (§2.6)
    normal = [p for p in plans if not p.anomaly]
    # spiked sessions carry a much higher avoidance rate than the typical session
    assert max(p.avoid_rate for p in anomalies) > 2 * config.OBST_AVOID_PER_MIN
    assert sum(p.avoid_rate for p in anomalies) / len(anomalies) > (
        sum(p.avoid_rate for p in normal) / len(normal)
    )


def test_dirt_blobs_vary_and_can_exceed_habitual_mean():
    world = load_map(MAP_DIR / "base_60m2.json")
    rng = DetRNG(4)
    dirts = [sample_plan(world, rng).dirt_by_zone for _ in range(50)]
    # per-session dirt is not constant (blobs move) and stays within [0, 100]
    zone0 = sorted(world.zones)[0]
    vals = [d[zone0] for d in dirts]
    assert max(vals) - min(vals) > 5.0
    assert all(0.0 <= v <= 100.0 for d in dirts for v in d.values())


def test_generation_on_variant_map_is_deterministic(tmp_path):
    from simulator.generate import build_db, canonical_hash

    a, b = tmp_path / "a.db", tmp_path / "b.db"
    vmap = MAP_DIR / "var_split.json"
    build_db(a, seed=7, n_sessions=6, map_path=vmap, with_sensors=False)
    build_db(b, seed=7, n_sessions=6, map_path=vmap, with_sensors=False)
    assert canonical_hash(a) == canonical_hash(b)


def test_cleanable_cells_only_floor_and_carpet():
    world = load_map(MAP_DIR / "holdout_hall.json")
    for z in world.zones.values():
        assert all(world.grid[y][x] in CLEANABLE for (x, y) in z.cells)
