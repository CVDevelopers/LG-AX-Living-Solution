# app

FastAPI application package: entrypoint, configuration, and the four layers (`api/`, `core/`, `db/`, `llm/`).

## Planned contents

- `main.py` — ASGI app; CORS: `localhost:5173` + 배포 오리진 (SPEC §6); mounted as a Vercel Python serverless function on profile W (§12.1)
- `config.py` — **every constant lives here** with `[Rn]` citation comments (§1 principle 4). Calibration output `data/calibration/calibrated.json` overrides defaults at load when the §2.5 gate passed. Includes `prior_source: reference | federated` (§11.2).
- `api/`, `core/`, `db/`, `llm/` — see each directory's README
