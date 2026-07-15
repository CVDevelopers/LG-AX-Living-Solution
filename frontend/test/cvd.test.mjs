// Accessibility gate (§7.3, §12.2): under colour-vision-deficiency simulation the teal heatmap
// ramp must keep its ORDINAL brightness (light = low p → dark = high p) and separate adjacent
// steps by ≥ 15 % lightness. "명도" is read as perceptual lightness (CIELAB L*, 0–100), so the
// threshold is ΔL* ≥ 15. Ordinal preservation is what actually protects the reading; the ≥15 %
// gap guarantees the steps stay distinguishable. Run: `node --test` (see package.json).

import assert from 'node:assert/strict'
import { test } from 'node:test'
import { RAMP_COLORS, hexToRgb } from '../src/heatmap/ramp.js'

const MIN_DELTA_L = 15 // ΔL* between adjacent ramp steps (§7.3 "명도차 ≥15%")

// Machado et al. (2009) severity-1.0 CVD simulation matrices, applied in linear RGB.
const CVD = {
  normal: [
    [1, 0, 0],
    [0, 1, 0],
    [0, 0, 1],
  ],
  protanopia: [
    [0.152286, 1.052583, -0.204868],
    [0.114503, 0.786281, 0.099216],
    [-0.003882, -0.048116, 1.051998],
  ],
  deuteranopia: [
    [0.367322, 0.860646, -0.227968],
    [0.28085, 0.672501, 0.046649],
    [-0.01182, 0.04294, 0.968881],
  ],
  tritanopia: [
    [1.255528, -0.076749, -0.178779],
    [-0.078411, 0.930809, 0.147602],
    [0.004733, 0.691367, 0.30390],
  ],
}

const srgbToLinear = (c) => {
  const s = c / 255
  return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4
}

const applyMatrix = (m, [r, g, b]) => [
  m[0][0] * r + m[0][1] * g + m[0][2] * b,
  m[1][0] * r + m[1][1] * g + m[1][2] * b,
  m[2][0] * r + m[2][1] * g + m[2][2] * b,
]

// CIELAB L* from linear-RGB relative luminance (D65, Yn = 1).
const lStar = ([r, g, b]) => {
  const y = Math.min(1, Math.max(0, 0.2126 * r + 0.7152 * g + 0.0722 * b))
  const f = y > 0.008856 ? Math.cbrt(y) : 7.787 * y + 16 / 116
  return 116 * f - 16
}

const rampLightness = (matrix) =>
  RAMP_COLORS.map((hex) => {
    const { r, g, b } = hexToRgb(hex)
    return lStar(applyMatrix(matrix, [srgbToLinear(r), srgbToLinear(g), srgbToLinear(b)]))
  })

for (const [name, matrix] of Object.entries(CVD)) {
  test(`ramp stays ordinal and ≥${MIN_DELTA_L}% apart under ${name}`, () => {
    const ls = rampLightness(matrix)
    for (let i = 1; i < ls.length; i++) {
      const delta = ls[i - 1] - ls[i] // ramp goes light → dark, so each step should drop
      assert.ok(delta > 0, `${name}: step ${i} not darker (L* ${ls[i - 1]} → ${ls[i]})`)
      assert.ok(
        delta >= MIN_DELTA_L,
        `${name}: step ${i} ΔL* ${delta.toFixed(1)} < ${MIN_DELTA_L}`,
      )
    }
  })
}
