# core/predict

The core prediction layer — an **online (continual-learning) estimator** (SPEC §3, §11.1). One distribution, one currency (§1 principle 7): interval, completion probability, state, heatmap, and planner approval all come from the same joint weighted bootstrap.

온라인 추정기. 세그먼트 스트림이 도착하는 대로 갱신되며(배치 재학습 없음), 전 층 공유 드리프트가 노화를 희소 층(예: 터보)에 자동 전파한다. 콜드 스타트는 별도 분기 없이 프라이어로 자동 수렴한다.

## Planned contents

- `segments.py` — homogeneous-segment extraction: mode 불변 ∧ charging=0 ∧ 단조 비증가, ≥ 3 min; weights λ^age × (Δt/10) (§3.1)
- `estimator.py` — stratum base rate (shrunk EWMA, half-life 40, k=3) × shared drift (EWMA, half-life 10) (§3.2)
- `bootstrap.py` — joint weighted bootstrap B=1,000: T* and T_req* computed in the same draw; dynamic reserve B_res (§3.2–3.3)
- `engines/` — v1 rule / v2 forgetting-factor RLS (γ=0.99, §3.4) / v3 quantile-LSTM serving via weights-JSON + NumPy forward pass (§3.5, §12.1)
- `contract.py` — engine contract `sample_rates(n)` / `quantiles()` + the 5-condition promotion gate (§3.7)
- `explain.py` — SHAP layer: v2 closed-form Shapley, v3 KernelSHAP, v1 rule factor decomposition — same output contract (§3.6)
- `state.py` — probability-currency state machine (0.90/0.80 thresholds) + hysteresis ±5 %p, n_eff<5 cap (§4.1)
- `planner.py` — zone-completion subset optimization 2⁵ × 3 modes s.t. P_S ≥ 0.90 (§5.1)
- `heatmap.py` — per-draw coverage rollout → cell completion probabilities, B=200 downsample (§5.2)

`state`/`planner`/`heatmap` are same-distribution consumers — the spec pins engines to `core/predict/`; these may move up to `core/` later without contract changes.
