# calibration

Committed calibration outputs (SPEC §2.5). (Directory name is project convention — the spec mandates the artifacts, not this exact path.)

오픈 데이터셋 캘리브레이션 산출물(커밋 대상). 주 1회 스케줄 워크플로가 재실행한다(§12.3).

## Contents

- `reference_anchors.json` — digitized literature anchor points (NASA PCoE [R7], OCV guides [R14][R15], UNIBO [R21]) used when the raw datasets are absent from `data/datasets/`. Not the raw data — the provenance is stated in the file.
- `calibration_report.md` — generated fit + gate report (`make calibrate`). With only anchors it is a **validation** run: OCV and β confirm the reference-profile defaults, α is flagged for a raw-data refit, and defaults are retained (no `calibrated.json` written). On gate failure the reason is recorded (§2.5).
- `overlay_sim_vs_measured.svg` — the sim-vs-measured OCV overlay figure (§8.5).
- `calibrated.json` — **written only by `calibrate --adopt` when raw datasets pass the gate** (① OCV RMSE ≤ 30 mV/cell ② α bootstrap CI excludes 0 ③ β ∈ [0.0002, 0.0006]); `config.py` overlays it at load time. Absent by default → defaults active. After adopting, regenerate `data/demo.db` so the sensor channels reflect the fit.
