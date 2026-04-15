---
date: 2026-04-14
topic: "Dynamic Feedback Loop & Intelligent Routing"
status: validated
---

## Problem Statement
The current routing system is static and "blind" to real-time performance fluctuations and task-specific strengths. It treats all failures as isolated events and doesn't proactively manage costs or context window limits.

## Constraints
- Must remain compatible with current SQLModel schema.
- Latency added by the scoring logic must be < 50ms.
- Must support the three core priorities: SPEED, COST, QUALITY.

## Approach
Implement a multi-layered intelligent router that combines:
1. **Real-time Health Monitoring:** Penalizes models based on very recent (5-10min) failures or latency spikes.
2. **Intent-Specific Quality:** Uses a matrix of performance per task type (Code, JSON, General).
3. **Pre-flight Budgeting:** Estimates tokens and cost BEFORE provider calls to prevent budget overruns.

## Architecture
- **`PromptEvaluator`**: Enhanced to estimate total tokens (prompt + history).
- **`RealTimeObserver`**: New service that queries recent `llm_attempts`.
- **`ScoringEngine`**: Updated to apply `HealthMultiplier` and `IntentWeight`.
- **`BudgetController`**: Validates estimated cost against user limits.

## Data Flow
1. **Request** -> `PromptEvaluator` (Intent, Complexity, Estimated Tokens).
2. **Scoring** -> `ScoringEngine` (Base Stats + Real-time Health + Intent Match).
3. **Budget Check** -> `BudgetController` (Compare estimated cost with limits).
4. **Execution** -> `FallbackExecutor` (Executes best candidate).
5. **Learning** -> `MetricsAggregator` (Updates snapshots with success/fail/latency/intent).

## Testing Strategy
- Unit tests for `ScoringEngine` with mocked "unhealthy" models.
- Integration tests for `BudgetController` with large mock prompts.
- Load tests to ensure the real-time health query is efficient.
