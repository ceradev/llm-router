from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from packages.services.prompt_evaluation import PromptEvaluator, PromptEvaluationResult


@pytest.fixture
def evaluator() -> PromptEvaluator:
    return PromptEvaluator()


def test_intent_code(evaluator: PromptEvaluator) -> None:
    r = evaluator.evaluate("Fix this python function and the sql query for the api")
    assert r.intent == "code"
    assert r.requires_code is True


def test_intent_analysis(evaluator: PromptEvaluator) -> None:
    r = evaluator.evaluate("Please analyze and compare two design architecture options")
    assert r.intent == "analysis"
    assert r.requires_reasoning is True


def test_intent_creative(evaluator: PromptEvaluator) -> None:
    r = evaluator.evaluate("Write a short story for a blog post, be creative")
    assert r.intent == "creative"


def test_intent_general(evaluator: PromptEvaluator) -> None:
    r = evaluator.evaluate("Hello there how are you today")
    assert r.intent == "general"


def test_complexity_in_range(evaluator: PromptEvaluator) -> None:
    r = evaluator.evaluate("x" * 2000)
    assert 0.0 <= r.complexity_score <= 1.0


def test_keywords_max_ten(evaluator: PromptEvaluator) -> None:
    r = evaluator.evaluate(
        "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron pi rho"
    )
    assert len(r.keywords) <= 10


def test_requires_json_flags(evaluator: PromptEvaluator) -> None:
    r = evaluator.evaluate("Return a json schema with structured output")
    assert r.requires_json is True


def test_requires_tools_flags(evaluator: PromptEvaluator) -> None:
    r = evaluator.evaluate("Use search to browse and fetch data via a tool")
    assert r.requires_tools is True


def test_estimated_tokens_positive(evaluator: PromptEvaluator) -> None:
    r = evaluator.evaluate("one two three four five")
    assert r.estimated_tokens >= 1


def test_prompt_evaluation_result_frozen() -> None:
    r = PromptEvaluationResult(
        intent="general",
        complexity_score=0.0,
        requires_reasoning=False,
        requires_code=False,
        requires_json=False,
        requires_tools=False,
        estimated_tokens=1,
        keywords=[],
    )
    with pytest.raises(FrozenInstanceError):
        r.intent = "code"  # type: ignore[misc]
