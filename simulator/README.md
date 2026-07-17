# simulator (offline lab)

Physics-based array-cleaning simulator — synthesizes the sensor/session logs the prediction engine consumes as if they were real-device logs. The prediction engine must never know this exists (SPEC §1 principle 1): when real device logs appear, only this lab gets swapped.

물리 기반 배열 청소 시뮬레이터(오프라인 랩). 세션 내 AR(1) 노이즈(§2.4b)로 "세션 내 소모율 상수" 가정이 시뮬레이터에 의해 자동 충족되는 순환을 차단해, 평가가 실전 난이도를 갖게 한다.

## Contents (M2)

- `battery.py` — load model P(t) (suction/floor/dirt/obstacle factors), discharge ΔSoC with η_rate + AR(1) noise (§2.4 a·b), and degradation `EFC += ΔSoC/100·w_mode → SoH = 1 − β·EFC` (§2.4d)
- `sensors.py` — voltage/current/temperature channels (§2.4c): 3-region OCV, `R_int` (aging + low-SoC knee), first-order thermal model, per-channel noise → `sensor_ticks` (1 s raw for the recent 20 sessions, 1 min summary earlier, §2.3)
- `world.py` — 0.5 m grid maps, cell encoding (−1 wall/0 floor/1 carpet/2 obstacle/9 dock), `dirt`/`zone_id` layers (§2.2)
- `rover.py` — coverage movement, mode switching, per-minute load trace + EFC, low-battery dock return & charge-and-resume (§2.6)
- `augment.py` — full §2.6 axes: start-SoC mix, mode mix, mid-session mode changes (10 %), aging (SoH input), spatial dirt (blobs + habitual zone), obstacle jitter, 5 % anomaly sessions
- `generate.py` — seed-fixed DB builder CLI (lifetime aging + sensor channels) + canonical determinism hash (§8.6, §12.2)
- `calibrate.py` — NASA PCoE / UNIBO fitting + §2.5 adoption gate → `data/calibration/` report + sim-vs-measured overlay (numpy-only; literature anchors when raw datasets are absent)
- `svgplot.py` — dependency-free deterministic SVG for the committed figures (§8.5)
- `train/` (M4) — v3 quantile-LSTM offline training (see its README)

Outputs three disjoint sets (separate seeds & maps): history 60 / training 2,000 / eval 500 sessions (§2.7).
