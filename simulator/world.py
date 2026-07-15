"""Seed-map loading for the offline simulator lab.

The parsing/geometry lives in ``backend.app.geo`` (backend-owned so the deployed server can
serve maps without importing ``simulator``, §12.1). This module just re-exports it so the
simulator's imports (``from .world import MapData`` / ``load_map``) keep working unchanged.
"""

from backend.app.geo import (
    CHAR_TO_CODE,
    CLEANABLE,
    DOCK,
    MapData,
    MapValidationError,
    ZoneInfo,
    cell_distance,
    load_map,
    load_map_data,
    zone_centroid,
)

__all__ = [
    "CHAR_TO_CODE",
    "CLEANABLE",
    "DOCK",
    "MapData",
    "MapValidationError",
    "ZoneInfo",
    "cell_distance",
    "load_map",
    "load_map_data",
    "zone_centroid",
]
