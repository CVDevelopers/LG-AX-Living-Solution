# tests

pytest suite (SPEC §8.3) — spans backend core, simulator physics, and E2E; runs as the CI PR gate (§12.2).

단위·통합 테스트. 백엔드 코어와 시뮬레이터 물리를 함께 다루므로 최상위에 둔다.

## Planned contents

- segment extraction (mode-change & charge-resume cases) · base×drift hand-computed 3 cases · n_eff
- joint bootstrap reproducibility (fixed seed) + T*–T_req* correlation check
- boundaries: B = B_res → 부족B, n_eff < 5 → state capped at '주의' · hysteresis
- heatmap rollout snapshot · physics discharge-curve snapshot · whatif ≡ predict batch equality
- engine contract conformance: downstream snapshots identical across v1/v2/v3 swap (§3.7)
- SHAP sanity · numeric guardrail · E2E
- `golden/` — golden files for the pure prediction core (see its README)

CI LLM tests use mocked fixed responses; real-LLM evaluation is a manual workflow (§12.4).
