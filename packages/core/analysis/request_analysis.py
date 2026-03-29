from __future__ import annotations

from dataclasses import dataclass

from packages.domain.gateway import GatewayTask, Intent, Priority


@dataclass(frozen=True)
class RequestAnalysisDraft:
    task_type: str
    complexity_score: float
    cost_sensitivity: float
    latency_sensitivity: float
    detected_skills: list[str]
    tokens_estimated: int


def _merge_skill_lists(base: list[str], extra: list[str] | None) -> list[str]:
    if not extra:
        return base
    seen = set(base)
    out = list(base)
    for tag in extra:
        if tag not in seen:
            seen.add(tag)
            out.append(tag)
    return out


def build_request_analysis_draft(
    *,
    task: GatewayTask,
    intent: Intent,
    complexity_score_override: float | None = None,
    tokens_estimated_override: int | None = None,
    extra_skills: list[str] | None = None,
    max_tokens_effective: int | None = None,
) -> RequestAnalysisDraft:
    prompt = task.prompt
    length = len(prompt)
    if complexity_score_override is not None:
        complexity_score = min(1.0, max(0.0, complexity_score_override))
    else:
        complexity_score = min(1.0, length / 2000.0)

    cost_sensitivity = 0.35
    latency_sensitivity = 0.35
    if task.priority == Priority.LOW_COST:
        cost_sensitivity = 1.0
    elif task.priority == Priority.LOW_LATENCY:
        latency_sensitivity = 1.0
    elif task.priority == Priority.HIGH_QUALITY:
        cost_sensitivity = 0.25
        latency_sensitivity = 0.25

    skills: list[str] = []
    match intent:
        case Intent.CODE:
            skills = ["code", "debugging"]
        case Intent.ANALYSIS:
            skills = ["analysis", "reasoning"]
        case Intent.CREATIVE:
            skills = ["creative", "writing"]
        case Intent.GENERAL:
            skills = ["general"]

    skills = _merge_skill_lists(skills, extra_skills)

    if tokens_estimated_override is not None:
        tokens_estimated = max(1, tokens_estimated_override)
    else:
        tokens_estimated = max(1, length // 4 + 64)
    cap = max_tokens_effective if max_tokens_effective is not None else task.max_tokens
    if cap is not None:
        tokens_estimated += cap

    return RequestAnalysisDraft(
        task_type=intent.value,
        complexity_score=complexity_score,
        cost_sensitivity=cost_sensitivity,
        latency_sensitivity=latency_sensitivity,
        detected_skills=skills,
        tokens_estimated=tokens_estimated,
    )
