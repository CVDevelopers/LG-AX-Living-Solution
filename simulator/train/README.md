# simulator/train

Offline training lab for the v3 quantile LSTM (SPEC §3.5): 1 layer, hidden 64, 3 quantile heads (p5/p50/p95), pinball loss, ≈ 20 k params, PyTorch, trained on the 2,000-session set with early stopping on validation pinball.

v3 퀀타일 LSTM 오프라인 학습 랩. 불확실성은 MC dropout이 아닌 퀀타일 헤드로 산출 — 결정적·재현 가능(고정 시드 스냅숏 테스트 가능). LSTM 재학습은 이 랩의 주기 작업이며, 스트리밍 적응은 본편의 공유 드리프트가 담당한다(§11.1).

**torch never ships in the deploy bundle** (§12.1): training exports weights as JSON, and serving is a NumPy forward pass in `backend/app/core/predict/engines/`. Checkpoints/runs are gitignored; the exported weights JSON is committed.
