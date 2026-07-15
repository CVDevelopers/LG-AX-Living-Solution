"""Seed-map loading and validation (SPEC §2.2).

Maps are hand-authored JSON: character rows for terrain plus digit rows for zone ids.
The loader converts to the §2.2 integer encoding (−1 wall / 0 floor / 1 carpet /
2 obstacle / 9 dock) and derives per-zone stats. A malformed map fails loudly here,
never downstream.
"""

import json
from dataclasses import dataclass
from pathlib import Path

CHAR_TO_CODE = {"#": -1, ".": 0, "c": 1, "o": 2, "D": 9}
WALL, FLOOR, CARPET, OBSTACLE, DOCK = -1, 0, 1, 2, 9
CLEANABLE = {FLOOR, CARPET}


@dataclass(frozen=True)
class ZoneInfo:
    zone_id: int
    name: str
    area_m2: float  # cleanable (floor + carpet) area
    carpet_ratio: float
    cells: tuple[tuple[int, int], ...]  # cleanable (x, y) cells, for tick positions
    has_obstacles: bool


@dataclass(frozen=True)
class MapData:
    map_id: str
    name: str
    cell_size_m: float
    grid: tuple[tuple[int, ...], ...]  # [y][x] terrain codes
    zone_grid: tuple[tuple[int, ...], ...]  # [y][x] zone ids (0 = none/wall)
    zones: dict[int, ZoneInfo]
    dock: tuple[int, int]
    raw: dict


class MapValidationError(ValueError):
    pass


def load_map(path: str | Path) -> MapData:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    rows, zone_rows = raw["rows"], raw["zone_rows"]

    if len(rows) != len(zone_rows):
        raise MapValidationError("rows and zone_rows must have the same height")
    width = len(rows[0])
    if any(len(r) != width for r in rows) or any(len(r) != width for r in zone_rows):
        raise MapValidationError("all rows must have equal width")

    grid, zone_grid, dock_cells = [], [], []
    for y, (row, zrow) in enumerate(zip(rows, zone_rows, strict=True)):
        grid_row, zone_row = [], []
        for x, (ch, zch) in enumerate(zip(row, zrow, strict=True)):
            if ch not in CHAR_TO_CODE:
                raise MapValidationError(f"unknown terrain char {ch!r} at ({x},{y})")
            if not zch.isdigit():
                raise MapValidationError(f"zone char must be a digit, got {zch!r} at ({x},{y})")
            code, zid = CHAR_TO_CODE[ch], int(zch)
            border = y in (0, len(rows) - 1) or x in (0, width - 1)
            if border and code != WALL:
                raise MapValidationError(f"border cell ({x},{y}) must be wall")
            if code == WALL and zid != 0:
                raise MapValidationError(f"wall cell ({x},{y}) must have zone 0")
            if code != WALL and zid == 0:
                raise MapValidationError(f"non-wall cell ({x},{y}) needs a zone id")
            if code == DOCK:
                dock_cells.append((x, y))
            grid_row.append(code)
            zone_row.append(zid)
        grid.append(tuple(grid_row))
        zone_grid.append(tuple(zone_row))

    if len(dock_cells) != 1:
        raise MapValidationError(f"map must contain exactly one dock, found {len(dock_cells)}")

    declared = {int(k): v["name"] for k, v in raw["zones"].items()}
    zones: dict[int, ZoneInfo] = {}
    for zid, zname in sorted(declared.items()):
        cells = [
            (x, y)
            for y, zrow in enumerate(zone_grid)
            for x, z in enumerate(zrow)
            if z == zid and grid[y][x] in CLEANABLE
        ]
        if not cells:
            raise MapValidationError(f"zone {zid} ({zname}) has no cleanable cells")
        n_carpet = sum(1 for (x, y) in cells if grid[y][x] == CARPET)
        has_obs = any(
            grid[y][x] == OBSTACLE and zone_grid[y][x] == zid
            for y in range(len(grid))
            for x in range(width)
        )
        cell_area = raw["cell_size_m"] ** 2
        zones[zid] = ZoneInfo(
            zone_id=zid,
            name=zname,
            area_m2=round(len(cells) * cell_area, 2),
            carpet_ratio=round(n_carpet / len(cells), 4),
            cells=tuple(cells),
            has_obstacles=has_obs,
        )

    used_zids = {z for zrow in zone_grid for z in zrow if z != 0}
    if used_zids != set(declared):
        raise MapValidationError(f"zone ids in grid {used_zids} != declared {set(declared)}")

    return MapData(
        map_id=raw["map_id"],
        name=raw["name"],
        cell_size_m=raw["cell_size_m"],
        grid=tuple(grid),
        zone_grid=tuple(zone_grid),
        zones=zones,
        dock=dock_cells[0],
        raw=raw,
    )
