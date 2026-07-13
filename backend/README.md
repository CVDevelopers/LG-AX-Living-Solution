# backend

FastAPI (Python 3.11) **thin server** (SPEC §1.1). Serves the REST API, hosts the pure prediction core, and proxies external LLM calls.

씬 서버. 기술적으로 서버는 필수가 아니지만(§1.1의 결정과 근거) 구조 리뷰 정합·scipy/sklearn 캘리브레이션·키 위탁을 위해 유지한다. 대신 **예측 코어는 순수 모듈로 격리**해 "서버 없이도 성립하는 설계"를 코드로 증명한다.

## Planned contents

- `app/` — FastAPI application package (entry, config, routers, core, db, llm proxy)
- SQLite via SQLAlchemy (§2.3); on Vercel profile W the DB ships as a read-only seed bundle and `/api/simulate` is disabled (§12.1)
