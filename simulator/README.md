# simulator (offline lab)

Physics-based array-cleaning simulator — synthesizes the sensor/session logs the prediction engine consumes as if they were real-device logs. The prediction engine must never know this exists (SPEC §1 principle 1): when real device logs appear, only this lab gets swapped.

물리 기반 배열 청소 시뮬레이터(오프라인 랩). 세션 내 AR(1) 노이즈(§2.4b)로 "세션 내 소모율 상수" 가정이 시뮬레이터에 의해 자동 충족되는 순환을 차단해, 평가가 실전 난이도를 갖게 한다.

## Contents (v0, M0)

- `battery.py` — load model P(t) (suction/floor/dirt/obstacle factors), discharge ΔSoC with η_rate + AR(1) noise (§2.4 a·b); OCV·R_int·temperature channels and SoH dynamics arrive in M2
- `world.py` — 0.5 m grid maps, cell encoding (−1 wall/0 floor/1 carpet/2 obstacle/9 dock), `dirt`/`zone_id` layers (§2.2)
- `rover.py` — coverage movement, mode switching, low-battery dock return & resume
- `augment.py` — M0 axes: start-SoC mix, mode mix, dirt fields, partial-zone subsets, mid-session mode changes (10 %); map variants/holdout maps/SoH slices/anomaly sessions arrive in M2 (§2.6)
- `generate.py` — seed-fixed DB builder CLI + canonical determinism hash (§8.6, §12.2)
- `calibrate.py` (M2) — NASA PCoE / UNIBO fitting + adoption gate → writes `data/calibration/` (§2.5)
- `train/` (M4) — v3 quantile-LSTM offline training (see its README)

Outputs three disjoint sets (separate seeds & maps): history 60 / training 2,000 / eval 500 sessions (§2.7).
