"""Segment extraction (SPEC §3.1) — the sample unit is the homogeneous segment, not the session.

A segment is a maximal run of minute intervals with constant mode, charging = 0 and
monotonically non-increasing battery, at least SEG_MIN_LEN_MIN minutes long. Sessions with
mid-run mode changes or charge-resume cycles are refined into their clean parts, not discarded.

Tick convention: a tick at minute t describes the interval that *ends* at t (the logger
samples after acting), so each interval takes the right-hand tick's mode and charging flag.
"""

from ... import config
from .types import Segment

# One tick per minute: (t_min, battery_pct, mode, charging)
Tick = tuple[int, float, str, int]


def extract_session_segments(ticks: list[Tick], age: int) -> list[Segment]:
    """Split one session's minute ticks into homogeneous segments."""
    ordered = sorted(ticks, key=lambda t: t[0])
    segments: list[Segment] = []
    run_mode: str | None = None
    run_dsoc = 0.0
    run_len = 0

    def flush() -> None:
        nonlocal run_mode, run_dsoc, run_len
        if run_mode is not None and run_len >= config.SEG_MIN_LEN_MIN and run_dsoc > 0:
            segments.append(Segment(age=age, mode=run_mode, dsoc=run_dsoc, dt_min=float(run_len)))
        run_mode, run_dsoc, run_len = None, 0.0, 0

    for i in range(len(ordered) - 1):
        t0, b0, _mode0, _chg0 = ordered[i]
        t1, b1, mode1, chg1 = ordered[i + 1]
        valid = chg1 == 0 and b1 <= b0 and t1 == t0 + 1
        if not valid:
            flush()
            continue
        if run_mode is not None and mode1 != run_mode:
            flush()
        if run_mode is None:
            run_mode = mode1
        run_dsoc += b0 - b1
        run_len += 1
    flush()
    return segments


def extract_segments(sessions_ticks: list[tuple[int, list[Tick]]]) -> list[Segment]:
    """Extract segments across sessions given (age, ticks) pairs."""
    out: list[Segment] = []
    for age, ticks in sessions_ticks:
        out.extend(extract_session_segments(ticks, age))
    return out
