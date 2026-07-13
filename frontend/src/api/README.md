# api

REST client for the backend endpoints (SPEC §6) and shared request/response shapes.

백엔드 REST 엔드포인트 클라이언트. 컴포넌트–API 의존 관계는 §7.4 표를 따른다: ForecastCard·ModeSelector → /predict, HeatmapView·PlanOverlay → /heatmap·/plan, MessageBanner → /predict·/next-plan, ReportView → /report, AgentPanel → /whatif·/plan·/next-plan, SimView → /sessions.

## Planned contents

- client functions for `/api/predict`, `/heatmap`, `/plan`, `/whatif`, `/next-plan`, `/plan-week`, `/sessions`, `/report/{id}`, `/simulate`, `/explain`, `/history`
- shared request/response shapes mirroring the §6 JSON, documented via JSDoc (incl. the `basis` block and common error shape)
