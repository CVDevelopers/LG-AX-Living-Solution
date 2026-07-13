# fedsim (offline lab)

Federated-learning simulation (SPEC §11.2) — produces a cold-start prior. Integrates with the estimator at exactly one point: `r_prior` in §3.2, via config `prior_source: reference | federated`.

연합 학습 시뮬레이션. 가상 가구 20곳(지도·모드 혼합비·SoH 단계 상이, §2.6 축 재사용)이 각자 로컬 층별 기저율만 적합하고, 서버는 세그먼트 수 가중 FedAvg로 전역 프라이어를 만든다 — 층별 계수 6개 + 표본 수만 왕복하며 원시 로그·지도는 미전송(온디바이스 테제와 동일한 프라이버시 서사).

## Planned contents

- 3-arm experiment — first-10-session MAE curves for a new home: (a) reference-profile prior (b) local-only (c) federated prior; expected result: (c) wins cold start (1 figure)
- weekly CI schedule re-runs this experiment (§12.3)

**Honesty limits (stated up front):** no differential privacy / secure aggregation claims, no real-deployment claims — "federated learning improves the cold-start prior, shown in simulation" and nothing more.
