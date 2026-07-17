# report

Session report + template narration (SPEC §9.5, §9.6, §3.6 v1). Backend-owned and serving-path
safe — imports `config` + core types only, never `simulator` (§1.1, §12.1).

## Contents

- `facts.py` — `ReportFacts`: plain, structured session facts (mode, consumption, completion,
  cleaned zones, inferred obstacle-anomaly flag). The API layer converts DB rows into these, the
  single place ORM meets report types.
- `explain.py` — v1 **rule factor decomposition** (§3.6): attributes a session's consumption
  deviation to `obstacle / carpet / dirt / aging` using the §2.4a power-model coefficients, in
  minutes of "consumed faster/slower". Signs are physical by construction, so the §8.1 sign-
  consistency gate holds. SHAP for v2/v3 replaces this contract in M4.
- `narrate.py` — the §9.6 template narrator (the M2 baseline voice and the final fallback, §9.3):
  facts + factors → 3–5 sentences, 해요체, one cleanup tip, a cause line for the dominant factor
  (the "off day" narration, §8.5). Every number is registered in an allowed set, so the §9.4
  numeric guardrail (`numbers_supported`) passes by construction — and will police the M3 LLM paths.

Served at `GET /api/report/{session_id}` → `{facts, factors, narration}`.
