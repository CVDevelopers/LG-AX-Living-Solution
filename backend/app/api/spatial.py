"""Spatial glue for M1 (§5): visit-order routing, dynamic reserve (§3.2), and the trajectory
heatmap (§5.2) / subset planner (§5.1) payloads (§6).

This layer joins map geometry (``backend.app.geo``) with the pure-core distribution
(``core.predict``): the same ``JointDraws`` feed the heatmap, the plan and the banner, so the
numbers can never disagree (§1 principle 7). No numbers are invented here — only arranged.
"""

import numpy as np

from .. import config
from ..core.predict import best_subset, rollout
from ..core.predict.types import Zone
from ..geo import MapData, cell_distance, zone_centroid

_RESERVE_MODE = config.MODES[-1]  # turbo: highest drain → conservative, mode-independent reserve


def visit_order(world: MapData, zone_ids: list[int]) -> list[int]:
    """Greedy nearest-neighbour tour from the dock over zone centroids (§3.3 travel term)."""
    remaining = list(zone_ids)
    order: list[int] = []
    cur: tuple[float, float] = world.dock
    while remaining:
        nxt = min(remaining, key=lambda z: cell_distance(zone_centroid(world.zones[z]), cur))
        order.append(nxt)
        cur = zone_centroid(world.zones[nxt])
        remaining.remove(nxt)
    return order


def dynamic_b_res(world: MapData, zone_ids: list[int], draws) -> float:
    """§3.2 reserve: clamp(p95(farthest-cell → dock return drain) + 2, 3, 8) %p.

    Priced at the highest-drain mode (turbo) so the reserve is conservative and independent of
    the mode being previewed — every endpoint in a request then shares one B_res (principle 7).
    """
    dock = world.dock
    far_cells = max(
        (cell_distance(cell, dock) for zid in zone_ids for cell in world.zones[zid].cells),
        default=0.0,
    )
    travel_min = far_cells * world.cell_size_m / config.V_TRAVEL_M_MIN
    p95_drain = float(np.percentile(draws.rates[_RESERVE_MODE] * travel_min, 95))
    return float(np.clip(p95_drain + 2.0, 3.0, 8.0))


def _serpentine(cells: tuple[tuple[int, int], ...]) -> list[tuple[int, int]]:
    """Boustrophedon sweep order within a zone — gives the heatmap a plausible trajectory feel."""
    by_row: dict[int, list[int]] = {}
    for x, y in cells:
        by_row.setdefault(y, []).append(x)
    ordered: list[tuple[int, int]] = []
    for i, y in enumerate(sorted(by_row)):
        for x in sorted(by_row[y], reverse=bool(i % 2)):
            ordered.append((x, y))
    return ordered


def build_heatmap(
    world: MapData,
    zones_by_id: dict[int, Zone],
    battery_pct: float,
    mode: str,
    draws,
    b_res: float,
    zone_ids: list[int] | None = None,
) -> dict:
    """§5.2 payload: per-cell completion probability + per-zone rollup, in visit order."""
    order = visit_order(world, list(zones_by_id) if zone_ids is None else zone_ids)
    zones_ordered = [zones_by_id[z] for z in order]

    cell_meta: list[tuple[int, int, int]] = []
    cells_frac: list[tuple[int, float]] = []
    for pos, zid in enumerate(order):
        cells = _serpentine(world.zones[zid].cells)
        n = len(cells)
        for rank, (x, y) in enumerate(cells, start=1):
            cell_meta.append((x, y, zid))
            cells_frac.append((pos, rank / n))

    zone_p, cell_p = rollout(zones_ordered, draws, mode, battery_pct, b_res, cells_frac)

    return {
        "mode": mode,
        "b_res": round(b_res, 2),
        "cell_size_m": world.cell_size_m,
        "grid": [list(row) for row in world.grid],
        "dock": list(world.dock),
        "cells": [
            {"x": x, "y": y, "zone": zid, "p": round(float(p), 3)}
            for (x, y, zid), p in zip(cell_meta, cell_p, strict=True)
        ],
        "zones": [
            {"zone_id": z.zone_id, "name": z.name, "order": i + 1, "p_complete": round(zp, 3)}
            for i, (z, zp) in enumerate(zip(zones_ordered, zone_p, strict=True))
        ],
    }


def build_plan(
    world: MapData,
    zones_by_id: dict[int, Zone],
    battery_pct: float,
    draws,
    b_res: float,
) -> dict | None:
    """§5.1 payload: the max-value zone subset that still completes at ≥ 0.90, with visit order
    and a dock→zone path for the PlanOverlay. Returns None when nothing completes → 부족B."""
    result = best_subset(battery_pct, list(zones_by_id.values()), draws, b_res)
    if result is None:
        return None

    order = visit_order(world, [z.zone_id for z in result.zones])
    return {
        "mode": result.mode,
        "b_res": round(b_res, 2),
        "zone_ids": order,
        "zones": [
            {
                "zone_id": zid,
                "name": zones_by_id[zid].name,
                "order": i + 1,
                "centroid": [round(c, 2) for c in zone_centroid(world.zones[zid])],
            }
            for i, zid in enumerate(order)
        ],
        "dock": list(world.dock),
        "p_complete": round(result.p_complete, 3),
        "t_req_min": round(result.t_req_min, 1),
        "remaining_pct": round(result.remaining_pct, 1),
        "value": round(result.value, 2),
    }
