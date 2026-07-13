# workflows

GitHub Actions (planned — the CI gate goes live with M0; SPEC §12.2–12.4).

CI/CD 워크플로. PR 게이트 실패 = 머지 차단. 전량(평가-500) 지표는 PR마다 돌리지 않고 스케줄 작업으로 분리한다.

## Planned contents

- `ci.yml` — PR gate: ruff·black·eslint·prettier → pytest (§8.3) → determinism (`simulate --seed 42` demo-DB hash equality) → frontend build → CVD contrast assertion (adjacent lightness Δ ≥ 15 %, §7.3) → quick-100 metric regression (MAE ≤ +10 % vs main) (§12.2)
- `nightly.yml` — full eval-500 (§8.1) + reliability diagram + ablation regeneration → artifact upload; auto-creates an issue on regression vs main (§12.3)
- `weekly.yml` — fedsim 3-arm experiment (§11.2) + calibration gate re-run (§2.5) — heavy jobs isolated (§12.3)
- `llm-eval.yml` — **manual trigger only**: real-LLM evaluations (§8.2, §9.5); regular CI uses mocked fixed responses (§12.4)

Secrets: external LLM keys and `X-API-Token` live in GitHub Secrets / Vercel env — never in the repo (§12.4).
