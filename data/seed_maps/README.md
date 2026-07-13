# seed_maps

Hand-authored JSON maps (SPEC §2.2). Cell = 0.5 m × 0.5 m; encoding `-1` wall / `0` floor / `1` carpet / `2` obstacle / `9` dock; layers `dirt`, `zone_id`. Schema will be documented here alongside a load-time validator.

수작업 JSON 지도 **5종**: 기본 60 m² 5구역 1종 + 변형 2종(학습·평가 공용) + **평가 전용 홀드아웃 2종**(§8.1 일반화 검증 — 학습에 미노출). GUI 지도 편집기는 범위 외.
