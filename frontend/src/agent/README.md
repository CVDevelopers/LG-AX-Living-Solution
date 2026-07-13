# agent

Forecast agent (SPEC §10) — *"the agent proposes, rules decide."* The LLM only interprets constraints, orders tool calls, and narrates rationale; all numbers come from predict/whatif/plan, and the only state change (`commit_next_plan`) requires explicit user confirmation.

예보 에이전트. 이중 모드 루프(§10.3): 온디바이스 = 추출-후-실행(LLM 1회 호출로 제약 JSON만 추출), API = 도구 루프(≤6콜). 정규식 슬롯 파서 폴백으로 LLM 없이도 성립한다(§10.5, 목표: 폴백 단독 충족 ≥ 80 %).

## Planned contents

- `tools.js` — JSON-Schema tool defs: get_prediction, evaluate_candidates, propose_plan, propose_week, explain_prediction, query_history, get_report, commit_next_plan (§10.2)
- `loop.js` — dual-mode agent loop (§10.3)
- `parser.js` — rule-fallback slot parser: minutes/zone-name dictionary/mode keywords (§10.5)
- `workflows/` — history Q&A, cause diagnosis, weekly planning, proactive suggestions (rule-triggered only) (§10.4)
- safety limits: ≤ 6 tool calls/request, whitelist only, 10 s timeout → fallback, tool JSON only re-injected into context (§10.6)
