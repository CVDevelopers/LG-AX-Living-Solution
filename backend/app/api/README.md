# api (routers)

REST endpoint routers (SPEC §6). JSON only; common error shape `{"error":{"code","message"}}`.

REST 라우터. 수치를 내는 모든 엔드포인트는 core/의 동일한 결합 부트스트랩 분포를 소비한다(§1 원칙 7) — 히트맵·구간·상태 간 모순이 구조적으로 불가능하다.

## Contents

- `routes.py` **(live, M0)** — `GET /api/predict` (T_est/interval, T_req/interval, p_complete, state, per_mode, basis), `GET /api/sessions`, `POST /api/simulate` (403 on profile W), `GET /api/health`

## Planned contents (M1+)
- `GET /api/heatmap` — grid + cell/zone completion probabilities (§5.2 semantics) — M1
- `POST /api/plan`, `POST /api/whatif`, `POST·GET /api/next-plan` — M1; `POST /api/plan-week` — M5
- `GET /api/report/{id}` — M2; `GET /api/explain` — top-3 factors (§3.6) — M4
- `GET /api/history` — **whitelisted query templates only**, no raw SQL — M5
- `POST /api/llm/proxy` — `X-API-Token` required (§9.2) — M3
