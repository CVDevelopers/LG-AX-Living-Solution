"""Session-plan sampling — M0 subset of the §2.6 augmentation axes.

Active axes: start-SoC mix, household mode mix, per-session dirt fields, partial-zone
subsets, mid-session mode changes (10 %). M2 adds map variants, holdout maps, SoH slices,
anomaly sessions and sensor-noise redraw.
"""

import numpy as np

from backend.app import config

from .rover import SessionPlan
from .world import MapData


def _pick_mode(rng: np.random.Generator) -> str:
    modes = list(config.MODE_MIX)
    probs = np.array([config.MODE_MIX[m] for m in modes])
    return str(rng.choice(modes, p=probs / probs.sum()))


def sample_plan(
    world: MapData, rng: np.random.Generator, allow_mode_change: bool = True
) -> SessionPlan:
    mode = _pick_mode(rng)

    if rng.random() < config.START_SOC_FULL_PROB:
        start_soc = 100.0
    else:
        start_soc = float(rng.uniform(*config.START_SOC_PARTIAL_RANGE))

    zone_ids = sorted(world.zones)
    if rng.random() >= config.FULL_CLEAN_PROB:
        k = int(rng.integers(1, min(3, len(zone_ids)) + 1))
        zone_ids = sorted(rng.choice(zone_ids, size=k, replace=False).tolist())

    dirt = {
        zid: float(np.clip(rng.normal(config.DIRT_MEAN, config.DIRT_SIGMA), 0.0, 100.0))
        for zid in world.zones
    }

    mode_change = None
    if allow_mode_change and rng.random() < config.MODE_CHANGE_SESSION_PROB:
        other = [m for m in config.MODES if m != mode]
        mode_change = (int(rng.integers(5, 21)), str(rng.choice(other)))

    return SessionPlan(
        mode=mode,
        start_soc=start_soc,
        zone_ids=tuple(zone_ids),
        dirt_by_zone=dirt,
        mode_change=mode_change,
        soh=1.0,  # aging slices arrive with M2 (§2.6)
    )
