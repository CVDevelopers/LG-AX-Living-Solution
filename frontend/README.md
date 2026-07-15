# frontend

React 18 + JavaScript + Vite mobile-first web app (360–420 px) — the forecast UI. No TypeScript by project decision — shared shapes are documented with JSDoc where needed.

배터리 기상 예보의 사용자 화면. 헤더(배터리·설정) / ForecastCard / HeatmapView / MessageBanner / ModeSelector / AgentPanel와 탭(ReportView·SimView)을 한 화면에 담고, 자연어 보고서·예보 에이전트는 LLM 라우팅 계층(온디바이스 WebLLM ↔ 외부 API)을 통해 동작한다 (SPEC §7).

## Planned contents

- `src/components/` — ForecastCard, HeatmapView, MessageBanner, ModeSelector, PlanOverlay, AgentPanel, ReportNarrator
- `src/views/` — SimView (2.5D replay), ReportView, SettingsView
- `src/llm/` — LLMProvider router: on-device | external, numeric guardrail, template fallback (§9)
- `src/agent/` — forecast agent dual-mode loop (§10)
- `src/api/` — REST client for backend endpoints (§6)
- `src/storage/` — next_plan storage adapter: server | localStorage (§12.1)

M0 status: scaffold + `components/` (ForecastCard, MessageBanner, ModeSelector, BatteryHeader) + `api/` client are implemented; `views/`, `llm/`, `agent/`, `storage/` hold READMEs until their milestones (M1–M5). Dev server proxies `/api` → `localhost:8000`.
