# components

UI components for the single mobile screen (SPEC §7.1–7.3).

모바일 1화면을 구성하는 UI 컴포넌트. 시각 규칙(§7.3): teal 단일 색상 명도 램프 + 구역 % 텍스트 상시 + p<0.5 셀 사선 해칭(3중 부호화, 색 단독 의존 금지), 애니메이션은 transform/opacity만.

## Planned contents

- `ForecastCard` — T_est + [T_lo, T_hi] interval bar with T_req tick; click → basis tooltip ("세그먼트 41개 · 드리프트 ×1.05 · 프라이어 14 %") (§7.2)
- `HeatmapView` — trajectory-based cell completion probabilities, 200 ms transitions (§5.2)
- `MessageBanner` — state messages & action buttons per the §4.2 policy table
- `ModeSelector` — eco/standard/turbo; optimistic update ≤ 300 ms via per_mode cache (§7.2)
- `PlanOverlay` — route numbering overlay for the 부족A flow + [다음에 예약] (§7.2)
- `AgentPanel` — natural language in → proposal card with [적용]/[대안 보기] (§10)
- `ReportNarrator` — session-report narration display (§9.5–9.6)
