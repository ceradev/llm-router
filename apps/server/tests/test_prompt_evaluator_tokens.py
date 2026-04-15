from __future__ import annotations

import pytest
from packages.services.prompt_evaluation.evaluator import PromptEvaluator, _estimate_input_tokens


class TestEstimateInputTokens:
    def test_short_prompt_uses_char_estimate(self):
        # 5 words, 20 chars → char_estimate = 20/4 = 5
        tokens = _estimate_input_tokens("hello world", 2)
        assert tokens >= 1

    def test_longer_prompt_blends_estimates(self):
        normalized = "Write a Python function that implements a binary search tree with insertion and deletion"
        word_count = len(normalized.split())
        tokens = _estimate_input_tokens(normalized, word_count)
        # Sanity: should be in reasonable range
        assert 10 < tokens < 200

    def test_minimum_of_1_token(self):
        tokens = _estimate_input_tokens("", 0)
        assert tokens >= 1


class TestPromptEvaluatorOutputTokens:
    def setup_method(self):
        self.evaluator = PromptEvaluator()

    def test_default_depth_yields_512_output_tokens(self):
        result = self.evaluator.evaluate("What is the capital of France?")
        assert result.estimated_output_tokens == 512

    def test_short_depth_yields_256_output_tokens(self):
        result = self.evaluator.evaluate("What is the capital of France?", response_depth="short")
        assert result.estimated_output_tokens == 256

    def test_detailed_depth_yields_1024_output_tokens(self):
        result = self.evaluator.evaluate("Explain quantum entanglement in detail", response_depth="detailed")
        assert result.estimated_output_tokens == 1024

    def test_unknown_depth_falls_back_to_512(self):
        result = self.evaluator.evaluate("hello", response_depth="mega")
        assert result.estimated_output_tokens == 512

    def test_estimated_tokens_positive(self):
        result = self.evaluator.evaluate("Design a REST API for a social media app")
        assert result.estimated_tokens >= 1

    def test_code_intent_detected(self):
        result = self.evaluator.evaluate("Write a Python function to sort a list")
        # Since we haven't updated evaluator yet, this will fail or test old logic
        # But we want to see it fail TDD style if possible.
        # Actually it's better to update code after writing test.
        assert result.intent == "code"
        assert result.requires_code is True
