"""Fixed synthetic inputs shared by the golden test and the regeneration script."""

from backend.app.core.predict.types import Segment, SessionStat, Zone


def golden_inputs():
    zones = [
        Zone(1, "거실", 16.75, 0.2687, 50.0),
        Zone(2, "주방", 9.0, 0.0, 50.0),
        Zone(3, "침실", 12.5, 0.6, 50.0),
    ]
    segments = [
        Segment(age, mode, rate * 10.0, 10.0)
        for age, mode, rate in [
            (0, "standard", 0.88),
            (1, "standard", 0.92),
            (2, "eco", 0.60),
            (3, "turbo", 1.35),
            (4, "standard", 0.86),
            (6, "eco", 0.64),
            (8, "standard", 0.95),
            (12, "turbo", 1.28),
            (15, "standard", 0.83),
        ]
    ]
    stats = [
        SessionStat(age, mode, area, dur, carpet, changes, dsoc)
        for age, mode, area, dur, carpet, changes, dsoc in [
            (0, "standard", 14.0, 16.0, 0.25, 0, 14.1),
            (1, "standard", 22.0, 25.0, 0.20, 0, 23.0),
            (2, "eco", 12.0, 15.0, 0.10, 0, 9.0),
            (3, "turbo", 18.0, 16.0, 0.30, 0, 21.6),
            (4, "standard", 9.0, 10.0, 0.00, 0, 8.6),
            (6, "eco", 16.0, 20.0, 0.35, 0, 12.8),
            (8, "standard", 26.0, 30.0, 0.25, 0, 28.5),
            (12, "turbo", 12.0, 11.0, 0.15, 0, 14.1),
            (15, "standard", 20.0, 23.0, 0.30, 0, 19.1),
        ]
    ]
    return 42.0, "standard", zones, segments, stats
