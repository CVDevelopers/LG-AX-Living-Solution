# src

Application source root. The layout mirrors the architecture: `components/` + `views/` render state, `llm/` + `agent/` form the language layer, `api/` + `storage/` isolate I/O behind interfaces.

애플리케이션 소스 루트. 화면(components·views), 언어 계층(llm·agent), I/O 계층(api·storage)을 분리한다. 그래픽스는 판단에 관여하지 않는다 — 모든 수치는 백엔드의 결정적 엔진이 원본이다 (SPEC §1 원칙 2·5).
