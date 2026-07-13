# storage

Storage adapter interface (`server | local`) for user-scoped state, primarily `next_plan` (SPEC §12.1).

저장 계층 어댑터. 로컬 프로파일(L)에서는 서버 DB, Vercel 배포(W)에서는 localStorage — 공용 서버 DB에 두면 방문자 간 계획이 섞이므로 클라이언트 저장이 올바른 설계다. M6에서 네이티브 백엔드(Capacitor Preferences API)가 추가된다.

## Planned contents

- adapter interface + `server` / `local` implementations; `native` arrives in M6
