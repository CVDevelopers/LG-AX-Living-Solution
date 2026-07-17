# Calibration report (SPEC §2.5)

- Data source: **digitized literature anchors**
- Provenance: Digitized reference anchors from the cited literature (NASA PCoE [R7], OCV curve guides [R14][R15], UNIBO Powertools [R21]). These are published-value anchor points, NOT the raw datasets. Drop the raw NASA/UNIBO files into data/datasets/ and run `python -m simulator.calibrate --adopt` for an independent calibration that can auto-write calibrated.json (SPEC §2.5).

## Adoption gate

| Criterion | Result | Value | Threshold |
|---|---|---|---|
| ① OCV RMSE (per cell) | **PASS** | 20.68 mV (defaults 28.08 mV) | ≤ 30.0 mV |
| ② α bootstrap CI excludes 0 | **PASS** | α=0.0199, CI95 [0.0116, 0.0409] (default 0.05) | CI ∌ 0 |
| ③ β in range | **PASS** | β=0.000401 (default 0.0004) | [0.0002, 0.0006] |

**Gate: PASS**

## Fitted OCV breakpoints (pack V)

- SoC knots: [1.0, 0.85, 0.15, 0.0]
- Fitted: [16.8219, 15.8503, 14.0631, 12.1306]  ·  Default: [16.8, 15.8, 14.2, 12.0]

## Decision

Validation run against digitized literature anchors (raw datasets absent). OCV (RMSE 28.08 mV for the defaults) and β (0.000401) confirm the reference-profile constants; α anchor-fit (0.0199) sits below the default (0.05), matching the §2.5 note that α should be refit — an intentional flag, not a defect; it only moves once raw UNIBO data drives the fit. Per §2.5 (미통과 시 기본값 유지 spirit when raw data is unavailable) **defaults are retained** and `calibrated.json` is not written. Drop the raw NASA/UNIBO datasets into `data/datasets/` and run `--adopt` for an independent auto-adoption.

Overlay figure: `overlay_sim_vs_measured.svg` (§8.5).
