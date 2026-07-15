from backend.app.core.predict.types import SessionStat, Zone


def make_zones() -> list[Zone]:
    return [
        Zone(1, "거실", 16.0, 0.25, 50.0),
        Zone(2, "침실", 12.0, 0.6, 50.0),
    ]


def make_ticks(rates_by_mode: list[tuple[str, float, int]], start: float = 100.0):
    """Build minute ticks: consecutive (mode, rate %/min, minutes) blocks, no charging."""
    ticks, battery, t = [], start, 0
    ticks.append((t, battery, rates_by_mode[0][0], 0))
    for mode, rate, minutes in rates_by_mode:
        for _ in range(minutes):
            battery -= rate
            t += 1
            ticks.append((t, battery, mode, 0))
    return ticks


def make_stat(age=0, mode="standard", area=14.0, duration=16.0, carpet=0.2, dsoc=12.0, changes=0):
    return SessionStat(
        age=age,
        mode=mode,
        cleaned_area_m2=area,
        duration_min=duration,
        carpet_ratio=carpet,
        mode_changes=changes,
        dsoc=dsoc,
    )
