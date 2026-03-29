from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sqlmodel import Session

from packages.domain.models import Capability
from packages.infrastructure.db.repositories.model_repository import ModelRepository
from packages.infrastructure.db.repositories.provider_repository import ProviderRepository
from packages.infrastructure.db.seed_types import SeededModelUpsertParams

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SeededModelSpec:
    """Curated baseline: OpenRouter model segment and upstream provider slug."""

    external_model_id: str
    display_name: str
    source_provider: str
    supports_json: bool
    supports_tools: bool
    supports_vision: bool
    tier: str
    context_window: int | None
    max_output_tokens: int | None
    quality_score: int
    latency_score: int
    cost_score: int
    capabilities: frozenset[Capability]


CURATED_MODELS: tuple[SeededModelSpec, ...] = (
    SeededModelSpec(
        external_model_id="gpt-4o",
        display_name="OpenAI GPT-4o",
        source_provider="openai",
        supports_json=True,
        supports_tools=True,
        supports_vision=True,
        tier="premium",
        context_window=128_000,
        max_output_tokens=16_384,
        quality_score=5,
        latency_score=2,
        cost_score=1,
        capabilities=frozenset({Capability.GENERAL, Capability.CODE, Capability.ANALYSIS}),
    ),
    SeededModelSpec(
        external_model_id="claude-3-haiku",
        display_name="Anthropic Claude 3 Haiku",
        source_provider="anthropic",
        supports_json=True,
        supports_tools=True,
        supports_vision=True,
        tier="premium",
        context_window=200_000,
        max_output_tokens=4_096,
        quality_score=4,
        latency_score=4,
        cost_score=3,
        capabilities=frozenset({Capability.GENERAL, Capability.CODE, Capability.ANALYSIS}),
    ),
    SeededModelSpec(
        external_model_id="deepseek-coder",
        display_name="DeepSeek Coder",
        source_provider="deepseek",
        supports_json=True,
        supports_tools=True,
        supports_vision=False,
        tier="premium",
        context_window=128_000,
        max_output_tokens=8_192,
        quality_score=4,
        latency_score=3,
        cost_score=4,
        capabilities=frozenset({Capability.GENERAL, Capability.CODE, Capability.ANALYSIS}),
    ),
    SeededModelSpec(
        external_model_id="llama-3.1-70b-instruct",
        display_name="Meta Llama 3.1 70B Instruct",
        source_provider="meta-llama",
        supports_json=True,
        supports_tools=True,
        supports_vision=False,
        tier="premium",
        context_window=131_072,
        max_output_tokens=8_192,
        quality_score=3,
        latency_score=3,
        cost_score=4,
        capabilities=frozenset({Capability.GENERAL, Capability.CODE, Capability.ANALYSIS}),
    ),
    SeededModelSpec(
        external_model_id="mixtral-8x7b-instruct",
        display_name="Mistral Mixtral 8x7B Instruct",
        source_provider="mistralai",
        supports_json=True,
        supports_tools=True,
        supports_vision=False,
        tier="alternative",
        context_window=32_768,
        max_output_tokens=16_384,
        quality_score=3,
        latency_score=4,
        cost_score=4,
        capabilities=frozenset({Capability.GENERAL, Capability.CODE, Capability.ANALYSIS}),
    ),
)


@dataclass
class SeedResult:
    created: int = 0
    updated: int = 0
    routing_keys: list[str] = field(default_factory=list)


def seed_initial_models(session: Session) -> SeedResult:
    """Idempotent upsert of curated OpenRouter models, routing settings, and capabilities."""
    providers = ProviderRepository(session)
    models = ModelRepository(session)

    result = SeedResult()
    for spec in CURATED_MODELS:
        provider = providers.ensure_provider(slug=spec.source_provider)
        if provider.id is None:
            raise RuntimeError(f"Provider {spec.source_provider} must have an id after ensure")

        action, row = models.upsert_seeded_model(
            provider_id=provider.id,
            params=SeededModelUpsertParams(
                source_provider=spec.source_provider,
                external_model_id=spec.external_model_id,
                display_name=spec.display_name,
                supports_json=spec.supports_json,
                supports_tools=spec.supports_tools,
                supports_vision=spec.supports_vision,
                tier=spec.tier,
                context_window=spec.context_window,
                max_output_tokens=spec.max_output_tokens,
                quality_score=spec.quality_score,
                latency_score=spec.latency_score,
                cost_score=spec.cost_score,
                capabilities=spec.capabilities,
            ),
        )
        if action == "created":
            result.created += 1
        else:
            result.updated += 1
        result.routing_keys.append(row.routing_key)
        logger.info(
            "Seed %s model %s (source_provider=%s)",
            action,
            row.routing_key,
            spec.source_provider,
        )

    return result


def _cli_main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    from packages.infrastructure.db.session import engine

    with Session(engine) as session:
        out = seed_initial_models(session)
        session.commit()
    print(
        f"seed_initial_models: created={out.created} updated={out.updated} "
        f"models={len(out.routing_keys)}"
    )
    for rk in out.routing_keys:
        print(f"  - {rk}")


if __name__ == "__main__":
    _cli_main()
