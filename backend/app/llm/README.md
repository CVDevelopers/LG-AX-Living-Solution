# llm (proxy internals)

Server-side internals for `POST /api/llm/proxy` (SPEC §9.2): static `X-API-Token` auth (mismatch → 401 — blocks LAN/public-URL abuse of the team's API budget), provider whitelist, 10 req/min rate limit, 16 KB body cap, 10 s timeout.

외부 LLM 프록시 내부 구현. 키는 서버 `.env` / Vercel 환경 변수에만 존재하며 클라이언트에 노출되지 않는다. BYOK 경로는 이 프록시를 아예 경유하지 않는다(키는 사용자 localStorage, 서버리스 배포 호환).
