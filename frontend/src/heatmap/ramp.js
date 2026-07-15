// Single-hue (teal) brightness ramp for the trajectory heatmap (§7.3): light = low completion
// probability → dark = high. One hue with a monotone lightness ramp keeps the ordinal readable
// under colour-vision deficiency (verified in frontend/test/cvd.test.mjs), and it is never the
// only signal — zone % text is always shown and low-probability cells are hatched (triple coding).
//
// This module is the SINGLE source of the ramp: the component paints from it and the CI CVD gate
// asserts on it, so a colour change can never silently break the accessibility guarantee.

// Stops are ~evenly spaced in CIELAB L* so every step clears the ≥15 % gap even after CVD
// simulation (worst adjacent ΔL* ≈ 16.5; see the gate). Re-tune with frontend/test/cvd.test.mjs.
export const RAMP = [
  { max: 0.2, color: '#d7f8f0' },
  { max: 0.4, color: '#5acebb' },
  { max: 0.6, color: '#1a9988' },
  { max: 0.8, color: '#0b655b' },
  { max: 1.01, color: '#033a33' },
]

export const RAMP_COLORS = RAMP.map((s) => s.color)

// Cells below this completion probability also get diagonal hatching (§7.3, third code).
export const HATCH_BELOW = 0.5

export function pToColor(p) {
  for (const stop of RAMP) if (p < stop.max) return stop.color
  return RAMP[RAMP.length - 1].color
}

export function hexToRgb(hex) {
  const h = hex.replace('#', '')
  return {
    r: parseInt(h.slice(0, 2), 16),
    g: parseInt(h.slice(2, 4), 16),
    b: parseInt(h.slice(4, 6), 16),
  }
}
