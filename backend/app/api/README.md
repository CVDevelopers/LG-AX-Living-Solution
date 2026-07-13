# api (routers)

REST endpoint routers (SPEC §6). JSON only; common error shape `{"error":{"code","message"}}`.

REST 라우터. 수치를 내는 모든 엔드포인트는 core/의 동일한 결합 부트스트랩 분포를 소비한다(§1 원칙 7) — 히트맵·구간·상태 간 모순이 구조적으로 불가능하다.

## Planned contents

- `predict.py` — `GET /api/predict`: T_est/interval, T_req/interval, p_complete, state, per_mode, basis
- `heatmap.py` — `GET /api/heatmap`: grid + cell/zone completion probabilities (§5.2 semantics)
- `plan.py` — `POST /api/plan`, `POST /api/whatif` (batch candidate eval, agent tool), `POST·GET /api/next-plan`, `POST /api/plan-week` (deterministic weekly scheduler)
- `explain.py` — `GET /api/explain`: top-3 factors {feature, direction, contribution_min} (§3.6)
- `history.py` — `GET /api/history`: **whitelisted query templates only** (template id + period/zone/mode params) — no raw SQL, no free-form queries
- `sessions.py` — `GET /api/sessions`, `GET /api/report/{id}`, `POST /api/simulate` (seed-fixed demo DB; disabled on profile W)
- `llm_proxy.py` — `POST /api/llm/proxy`: `X-API-Token` required (§9.2)
