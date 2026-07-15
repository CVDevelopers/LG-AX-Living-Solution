"""Platform- and version-independent RNG for reproducible data generation (SPEC §12.2).

numpy's ``Generator`` distribution methods are NOT reproducible across numpy versions or
CPU/libm platforms — ``normal`` (ziggurat) and ``poisson`` (rejection) consume a *variable*
number of raw draws, so the first cross-platform disagreement in a tail/rejection case
cascades into a completely different stream. The CI determinism gate (§12.2) caught demo.db
diverging between macOS-arm64 and Linux-x64 for exactly this reason.

Only ``Generator.random()`` — the canonical uniform ``(uint64 >> 11) · 2⁻⁵³`` — is stable
everywhere. This wrapper derives every quantity from ``random()`` with FIXED consumption per
call, so the stream can never misalign. The one transcendental path (Box–Muller ``normal``)
consumes exactly two uniforms regardless of value; its last-ULP platform differences only ever
reach values that are rounded to ≥3 decimals before storage, so they are absorbed.
"""

import math

import numpy as np


class DetRNG:
    def __init__(self, seed: int):
        self._rng = np.random.default_rng(seed)

    def random(self) -> float:
        """Stable uniform in [0, 1)."""
        return float(self._rng.random())

    def uniform(self, lo: float, hi: float) -> float:
        return lo + (hi - lo) * self.random()

    def integers(self, lo: int, hi: int) -> int:
        """Uniform int in [lo, hi) from one stable uniform (version-independent)."""
        return lo + int(self.random() * (hi - lo))

    def bernoulli(self, p: float) -> int:
        """0/1 with P(1) = p — a pure uniform-vs-constant compare, bit-identical everywhere."""
        return int(self.random() < p)

    def normal(self, mu: float = 0.0, sigma: float = 1.0) -> float:
        """Box–Muller — fixed two-uniform consumption keeps the stream aligned across platforms."""
        u1 = self.random()
        if u1 < 1e-300:  # guard log(0); probability ~2⁻⁵³·… negligible but deterministic
            u1 = 1e-300
        u2 = self.random()
        z = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
        return mu + sigma * z

    def choice_p(self, items, probs):
        """Inverse-CDF selection consuming one stable uniform (probs need not be normalized)."""
        u = self.random() * float(sum(probs))
        cumulative = 0.0
        for item, weight in zip(items, probs, strict=True):
            cumulative += weight
            if u < cumulative:
                return item
        return items[-1]

    def choice(self, items):
        return items[self.integers(0, len(items))]

    def sample_without_replacement(self, items, k: int):
        """k distinct items via partial Fisher–Yates using stable integer draws."""
        pool = list(items)
        picked = []
        for _ in range(k):
            picked.append(pool.pop(self.integers(0, len(pool))))
        return picked
