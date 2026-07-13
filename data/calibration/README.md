# calibration

Committed calibration outputs (SPEC §2.5). (Directory name is project convention — the spec mandates the artifacts, not this exact path.)

오픈 데이터셋 캘리브레이션 산출물(커밋 대상). 주 1회 스케줄 워크플로가 재실행한다(§12.3).

## Contents

- `calibrated.json` — constants override, applied over `config.py` defaults **only when the adoption gate passes**: ① OCV RMSE ≤ 30 mV/cell ② α bootstrap CI excludes 0 ③ β ∈ [0.0002, 0.0006]
- `calibration_report.md` — generated fit report; on gate failure, defaults stay and the reason is recorded
