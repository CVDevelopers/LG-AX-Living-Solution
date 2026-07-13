# llm

Path-selectable LLM service layer (SPEC §9). Every LLM feature works on any path — external API → on-device → rule fallback (§9.3) — and LLMs never produce numbers (§1 principle 5): all output passes the numeric guardrail or is discarded.

경로 선택형 LLM 서비스 계층. 기본은 온디바이스(WebLLM, 프라이버시 지향), 옵트인 시 외부 API(프록시 또는 BYOK). 어느 단이 실패해도 규칙 폴백으로 기능이 성립한다.

## Planned contents

- `provider.js` — `LLMProvider` contract + router (§9.1)
- `ondevice/` — WebLLM(WebGPU) provider; Wi-Fi + WebGPU detection gate, auto-fallback (§9.1)
- `external/` — proxy client (`X-API-Token`) + BYOK direct client (key in localStorage, no proxy) (§9.2)
- `guardrail.js` — extract every number → cross-check against input facts & allowed derivations → discard on a single mismatch, log per-path discard rate (§9.4)
- `templates/` — template engine: fact fields → sentence slots; baseline & final fallback, same input contract as LLM (§9.6)
