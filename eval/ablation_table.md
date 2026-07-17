# Ablation table (§8.5)

Time MAE at SoH 0.8 (ramped-aging history), each stage adding one estimator component.
RLS (v2) and LSTM (v3) rows arrive in M4.

| Stage | Time MAE (min) | Δ vs prev |
|---|---|---|
| raw | 3.149 | — |
| +ewma | 3.025 | -0.124 |
| +shrink | 3.912 | +0.887 |
| +drift | 2.404 | -1.508 |
| +RLS (v2) | — (M4) | |
| +LSTM (v3) | — (M4) | |
