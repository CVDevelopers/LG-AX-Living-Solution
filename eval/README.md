# eval

Evaluation harness for the SPEC §8.1 metric suite. (The directory name is project convention — the spec mandates the artifacts, not this exact path.)

평가 하니스. 평가 전용 500세션(홀드아웃 지도 2종 + 경화 슬라이스 포함, 이력·학습과 시드·지도 분리 §2.7)에서 전 지표를 산출한다.

## Contents

- `quick100.py` **(live, M0)** — 100 eval sessions (seed 4242, disjoint from history): time MAE, T_req MAE, consumption MAPE, 90 % interval coverage. `--check` is the CI regression gate (time MAE ≤ baseline ×1.10, §12.2); `baseline_quick100.json` is committed. Note: time MAE extrapolates T_actual to the reserve level, so errors scale with the full-battery horizon (~2 h) — the §8.1 ≤ 2.0 min target is judged on the M2 eval-500 design.

## Planned contents

- `eval-500` — full suite: time MAE ≤ 2.0 min · T_req MAE ≤ 2.0 min · consumption MAPE ≤ 12 % · 90 % coverage within 86–94 % · state agreement ≥ 90 % · aging slice (SoH 0.8) MAE ≤ 2.5 min · hardened slices (AR(1)/holdout maps/mode-change) · SHAP sign consistency ≥ 95 % · v3 generalization ≤ 1.2 · v3 cold start ≤ +10 % (§8.1)
- reliability diagram (10-bin, predicted P vs observed frequency — "our 92 % is really 92 %") and ablation table (raw mean → +EWMA → +shrinkage → +drift → +RLS → +LSTM) (§8.5)
- nightly full run + artifact upload, auto-issue on regression; weekly lab jobs are separate (§12.3)
