# db

SQLAlchemy models + SQLite session management for the SPEC §2.3 schema.

## Planned contents

- models: `zones`, `sessions`, `ticks` (1 min 해상도), `sensor_ticks` (1 s 해상도, NASA PCoE 필드 준용), `next_plan` (§2.3)
- `grid_maps` — named in the §1 architecture diagram but **missing from the §2.3 DDL** (spec discrepancy — resolve in M0; presumably per-session persisted seed-map grids)
- retention policy: sensor_ticks 최근 20세션은 1 s 원본 유지, 이전 세션은 1 min 요약 후 삭제, simulate 시 압축 (§2.3)
- profile W: DB is a read-only seed bundle generated at build time (§12.1)
