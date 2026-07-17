"""Template narration (SPEC §9.6) — the M2 baseline report voice and the final fallback (§9.3).

Facts + factors → sentence slots, 해요체, 3–5 sentences, one cleanup tip, with a cause sentence
for the dominant factor (the "off day" narration, §8.5). Every number is inserted from a fact and
registered in the allowed set, so the §9.4 numeric guardrail passes by construction — and the same
guardrail will police the LLM narration paths that arrive in M3.
"""

import re

from .explain import Factor
from .facts import ReportFacts

_MODE_KR = {"eco": "절약", "standard": "표준", "turbo": "강력"}
_CAUSE = {
    "obstacle": "장애물 회피가 잦아 평소보다 약 {c}분 빨리 소모됐어요.",
    "carpet": "카펫 구역이 많아 평소보다 약 {c}분 더 소모됐어요.",
    "dirt": "오염이 심한 구역이 있어 평소보다 약 {c}분 더 소모됐어요.",
    "aging": "배터리 노화로 소모가 평소보다 약 {c}분 빨라졌어요.",
}
_TIP = {
    "obstacle": "바닥의 장애물을 미리 치워두면 다음 청소가 더 빨라져요.",
    "carpet": "카펫이 많은 구역은 따로 예약해 나눠 청소하면 효율적이에요.",
    "dirt": "자주 더러워지는 구역은 청소 주기를 조금 늘려보세요.",
    "aging": "배터리 성능이 서서히 낮아지고 있어요. 완충 상태를 자주 유지해 주세요.",
}
_MIN_CAUSE_MIN = 0.5  # only surface a cause factor worth at least this many minutes


def _fmt(v: float) -> str:
    v = round(float(v), 1)
    return str(int(v)) if abs(v - round(v)) < 1e-9 else f"{v:g}"


def numbers_supported(text: str, allowed: set[float], tol: float = 0.06) -> bool:
    """§9.4 guardrail: every number in the text must match a fact-derived value within ``tol``."""
    for tok in re.findall(r"\d+(?:\.\d+)?", text):
        v = float(tok)
        if not any(abs(v - a) <= tol for a in allowed):
            return False
    return True


def narrate(facts: ReportFacts, factors: list[Factor]) -> dict:
    """Return ``{text, guardrail_ok, top_factor}`` — the §9.6 template report for one session."""
    allowed: set[float] = set()

    def num(v: float) -> str:
        allowed.add(round(float(v), 1))
        return _fmt(v)

    month, day = int(facts.started_at[5:7]), int(facts.started_at[8:10])
    mode_kr = _MODE_KR.get(facts.mode, facts.mode)
    sentences = [
        f"{num(month)}월 {num(day)}일 {mode_kr} 모드로 {num(facts.cleaned_area_m2)}㎡를 "
        f"{num(facts.duration_min)}분 동안 청소했어요."
    ]

    if facts.charged:
        sentences.append("청소 중 배터리가 부족해 충전한 뒤 남은 구역을 이어서 청소했어요.")
    elif facts.completed:
        sentences.append(f"배터리 {num(facts.dsoc)}%로 전체 청소를 마쳤어요.")
    elif facts.dock_returns > 0:
        sentences.append(
            f"배터리 {num(facts.dsoc)}%를 쓰고 {num(facts.end_battery)}%에서 도크로 돌아왔어요."
        )
    else:
        sentences.append(f"배터리 {num(facts.dsoc)}%를 사용했어요.")

    top = factors[0] if factors else None
    # Skip the numeric cause for charge-resume sessions — their runtime includes charging, so a
    # single-factor attribution over it would overstate (§3.1). Everything else gets the cause line.
    if (
        top
        and not facts.charged
        and abs(top.contribution_min) >= _MIN_CAUSE_MIN
        and top.feature in _CAUSE
    ):
        sentences.append(_CAUSE[top.feature].format(c=num(abs(top.contribution_min))))

    if facts.mode_changes > 0:
        sentences.append("청소 도중 모드를 바꿔 진행했어요.")

    tip_key = top.feature if top else "aging"
    sentences.append(_TIP.get(tip_key, _TIP["aging"]))

    text = " ".join(sentences[:5])  # keep it to 3–5 sentences (§9.6)
    return {
        "text": text,
        "guardrail_ok": numbers_supported(text, allowed),
        "top_factor": top.feature if top else None,
    }
