# core

Pure, portable domain layer — ★ no FastAPI/SQLAlchemy/simulator imports (SPEC §1.1). Purity is guaranteed by golden-file tests (§8.3).

순수 도메인 계층 — "서버 없이도 성립하는 설계"의 증명이자 클라이언트 이식 가능 모듈. 입력은 DB 로그뿐이며(§1 원칙 1), 시뮬레이터 상수 직접 주입은 금지 — 소모율은 로그에서 *추정*한다(원칙 3, 자기 채점 순환 방지).

## Planned contents

- `predict/` — the prediction layer: engines, joint bootstrap, and same-distribution consumers (see its README)
