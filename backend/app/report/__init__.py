"""Session report + template narration (SPEC §9.6, §3.6 v1 rule factor decomposition).

Backend-owned, serving-path safe: imports config + core types only, never ``simulator`` (§1.1,
§12.1). LLM narration paths arrive in M3; this template engine is the M2 baseline and the final
fallback (§9.3), sharing the same fact contract and the §9.4 numeric guardrail.
"""

from .explain import Factor, explain_session
from .facts import ReportFacts, build_facts
from .narrate import narrate, numbers_supported

__all__ = [
    "Factor",
    "ReportFacts",
    "build_facts",
    "explain_session",
    "narrate",
    "numbers_supported",
]
