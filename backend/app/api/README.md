# api (routers)

REST endpoint routers (SPEC §6). JSON only; common error shape `{"error":{"code","message"}}`.

REST 라우터. 수치를 내는 모든 엔드포인트는 core/의 동일한 결합 부트스트랩 분포를 소비한다(§1 원칙 7) — 히트맵·구간·상태 간 모순이 구조적으로 불가능하다.

## Contents

- `routes.py` **(live, M0–M1)** —
  - `GET /api/predict` — T_est/interval, T_req/interval, p_complete, state (부족A/부족B split, §4.1), per_mode, basis; uses the §3.2 dynamic reserve from the map
  - `GET /api/heatmap` — grid + per-cell/per-zone completion probabilities (§5.2 trajectory rollout)
  - `POST /api/plan` — max-value zone subset that still completes at ≥ 0.90 (§5.1, 부족A)
  - `GET·POST /api/next-plan`, `POST /api/next-plan/{id}/consume` — carryover (§4.2); write-disabled on profile W (client-side store instead, §12.1)
  - `GET /api/sessions`, `POST /api/simulate` (403 on profile W), `GET /api/health`
- `spatial.py` **(live, M1)** — visit-order routing, dynamic reserve (§3.2), heatmap/plan payload builders; joins map geometry with the shared core distribution (§1 principle 7)

## Planned contents (M2+)
- `POST /api/whatif` (agent batch eval), `POST /api/plan-week` — M5
- `GET /api/report/{id}` — M2; `GET /api/explain` — top-3 factors (§3.6) — M4
- `GET /api/history` — **whitelisted query templates only**, no raw SQL — M5
- `POST /api/llm/proxy` — `X-API-Token` required (§9.2) — M3
