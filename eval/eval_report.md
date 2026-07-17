# Evaluation report — eval-500 (SPEC §8.1)

n = 500 sessions · 5 SoH cohorts × 100 · maps: 3 train + 2 holdout · seed 500042

## §8.1 targets

| Metric | Value | Target |  |
|---|---|---|---|
| Time MAE (start ≤25 %) | 0.973 min | ≤ 2.0 | ✅ |
| T_req MAE (completed) | 1.683 min | ≤ 2.0 | ✅ |
| Consumption MAPE | 6.38 % | ≤ 12.0 | ✅ |
| 90 % coverage | 84.9 % | 86.0–94.0 | ❌ |
| State agreement | 98.3 % | ≥ 90 | ✅ |
| Aging — SoH 0.8 | 0.709 min | ≤ 2.5 | ✅ |

Overall time MAE (all start batteries) is 3.579 min — it scales with the battery range projected, so the decision-relevant low-battery band is the headline (the ≤2-min target was derived for ~14-min sessions, §8.1). MAPE is the battery-independent rate-error headline.

**Coverage 84.9 %** sits just under the 86 % floor; at n=500 the coverage sampling CI is ±2.6 pp (§2.7), so it overlaps the band. The residual under-coverage is a genuine generalization effect — the 90 % interval is fit on the 3 train maps, while 40 % of eval sessions run the 2 holdout maps and 5 % are obstacle-spike anomalies, whose rate tails the train-fit interval does not fully span. It does not shrink with more history (it is predictive, not estimator, variance), so it is reported, not tuned away (§8.1 DoD).

## Time MAE by start-battery band

| Start battery | n | Time MAE (min) |
|---|---|---|
| 0-25 % | 46 | 0.973 |
| 25-50 % | 90 | 2.277 |
| 50-75 % | 104 | 4.19 |
| 75-100 % | 118 | 5.048 |

## Hardened slices (§8.1 경화 슬라이스 — sim/model circularity check)

Time MAE on the decision band (start ≤25 %). AR(1) noise is on in every session, so the whole clean band is the AR(1) slice.

| Slice | n | Time MAE (min) |
|---|---|---|
| AR(1) noise (clean, decision band) | 46 | 0.973 |
| Holdout maps (unlearned layouts) | 23 | 0.994 |
| Train maps | 23 | 0.952 |
| Holdout / train ratio |  | 1.044 |

Contaminated sessions (mid-session mode change, charge-resume) are refined into clean segments (§3.1), not scored session-level. Their segment-rate MAPE tracks the clean baseline → refinement, not corruption:

| Segment source | n segments | Rate MAPE (%) |
|---|---|---|
| Clean sessions | 358 | 6.38 |
| Mode-change sessions | 63 | 8.19 |
| Charge-resume sessions | 223 | 7.32 |

## Session mix

clean 358 · charge-resume 110 · mode-change 37 · anomaly 17 · holdout-map 200

Artifacts: `reliability_diagram.svg`, `ablation_table.md`, `report_eval500.json`.
