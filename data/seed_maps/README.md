# seed_maps

Hand-authored JSON maps (SPEC §2.2). Cell = 0.5 m × 0.5 m; encoding `-1` wall / `0` floor / `1` carpet / `2` obstacle / `9` dock; a terrain-char grid (`rows`) plus a zone-digit grid (`zone_rows`). Validated at load time by `backend/app/geo.py` (border walls, exactly one dock, every non-wall cell zoned, declared == used zones).

수작업 JSON 지도 **5종**: 기본 60 m² 5구역 1종 + 변형 2종(학습·평가 공용) + **평가 전용 홀드아웃 2종**(§8.1 일반화 검증 — 학습에 미노출). GUI 지도 편집기는 범위 외.

| File | Role | Zones | Layout |
|---|---|---|---|
| `base_60m2.json` | base | 5 | 기본 60 m² 5구역 |
| `var_split.json` | train variant | 5 | central corridor splitting four rooms |
| `var_open.json` | train variant | 5 | open plan + peripheral rooms |
| `holdout_studio.json` | eval-only holdout | 4 | compact studio, off-centre dock |
| `holdout_hall.json` | eval-only holdout | 6 | long hallway spine with side rooms |

Train maps (base + 2 variants) fit the eval-500 cohort histories; the 2 holdout maps are used only for evaluation to measure generalization (§2.2, §8.1). `config.TRAIN_MAP_FILES` / `config.HOLDOUT_MAP_FILES` are the source of truth.
