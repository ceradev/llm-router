date: 2026-04-14
topic: "Enterprise Routing Engine & Fast-Track"
status: validated

## Problem Statement
The current routing system is inefficient for production use. It evaluates every model candidate for every request, wasting credits and introducing unnecessary latency. Additionally, the scoring logic is superficial, and the system relies too heavily on a single aggregator (OpenRouter).

## Constraints
- Must reduce token expenditure on prompt evaluation by at least 80% for verified models.
- Must maintain backward compatibility with existing DB schemas while extending them.
- Must support multiple providers directly (OpenAI, Anthropic, Groq).
- UI must remain intuitive while providing data-driven alternatives.

## Approach
Implement a **Stability-First** architecture. We will introduce a **Fast-Track** lane for "Verified" models that bypasses real-time evaluation, using cached performance snapshots instead. The engine will evolve into a **Multidimensional Scoring Engine** that adapts weights based on prompt intent and incorporates a **Multi-Provider Strategy** for maximum resilience.

## Architecture
- **Tiered Selection:** Models are categorized into Tier 1 (Verified/Stable) and Tier 2 (Provisional/Experimental).
- **Snapshot-Based Scoring:** Verified models use pre-calculated scores adjusted by real-time latency/cost metrics.
- **Direct-Path Execution:** Preferred use of direct provider APIs over aggregators when latency/cost is better.

## Components
- **ModelSelector (v2):** Implements Tiered Filtering. Prioritizes Verified models unless in "Discovery Mode".
- **ScoringEngine (v2):** Uses dynamic weighting (Intent-based) and incorporates Jitter/Reliability penalties.
- **ProviderRegistry (v2):** Manages multiple connections per model (e.g., GPT-4o via OpenAI and via OpenRouter).
- **FallbackExecutor (v2):** Handles cross-provider failover and marks models as "Broken" in DB upon failure.

## Data Flow
1. **Request:** Prompt + Context.
2. **Selector:** Checks DB for Verified models matching technical requirements.
3. **Engine (Fast-Track):** If Verified models are found, applies snapshot scoring. No external evaluation tokens spent.
4. **Execution:** Calls Direct Provider. Fallback to Aggregator if needed.
5. **Observation:** Metrics (Latency, Status) are updated in DB to refine future snapshots.

## Error Handling
- **Circuit Breaker:** Automatic status change to `broken` or `degraded` after X consecutive failures.
- **Graceful Degradation:** If all Verified models fail, the system unlocks Tier 2 (Provisional) models as an emergency backup.

## Testing Strategy
- **Shadow Routing:** Run the new engine in parallel with the old one, logging differences in "Champion" selection without affecting production traffic.
- **Chaos Testing:** Simulate provider outages to verify the Multi-Provider fallback logic.
- **Cost Audit:** Compare token usage before and after Fast-Track implementation.
