"""Plain input types for the pure prediction core (SPEC §1.1).

The core consumes only these — never ORM rows, never simulator objects.
`age` is measured in sessions counted back from the most recent one (latest = 0).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Segment:
    """Homogeneous discharge segment (§3.1): mode-constant, charging-free, monotone."""

    age: int
    mode: str
    dsoc: float  # battery percentage points consumed over the segment (> 0)
    dt_min: float  # segment length in minutes (>= SEG_MIN_LEN_MIN)

    @property
    def rate(self) -> float:
        return self.dsoc / self.dt_min


@dataclass(frozen=True)
class SessionStat:
    """Per-session aggregates for coverage speed ṽ (§3.3) and predictive residuals (§3.2)."""

    age: int
    mode: str
    cleaned_area_m2: float
    duration_min: float
    carpet_ratio: float
    mode_changes: int = 0
    dsoc: float = 0.0  # start_battery − end_battery (session-level consumption)


@dataclass(frozen=True)
class Zone:
    zone_id: int
    name: str
    area_m2: float
    carpet_ratio: float
    avg_dirt: float
