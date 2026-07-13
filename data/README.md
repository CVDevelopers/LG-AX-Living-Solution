# data

Committed data assets plus a gitignored landing spot for raw open datasets.

커밋되는 데이터 자산과, 커밋하지 않는 원시 데이터셋의 자리.

## Contents

- `seed_maps/` — hand-authored JSON maps (SPEC §2.2) — **committed**
- `calibration/` — calibration outputs `calibrated.json` + `calibration_report.md` (§2.5) — **committed**
- `datasets/` — NASA PCoE / UNIBO raw downloads (§2.5) — **gitignored**, README only
- `demo.db` — seed-fixed demo DB, arrives in M0 — **committed by design** (§8.6); CI re-runs `simulate --seed 42` and asserts hash equality (§12.2); bundled read-only on Vercel profile W (§12.1)
