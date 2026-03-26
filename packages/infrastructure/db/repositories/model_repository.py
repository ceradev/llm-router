from __future__ import annotations

from dataclasses import dataclass

from sqlmodel import Session, select

from packages.domain.gateway import Intent, Priority
from packages.domain.models import Capability, ModelProfile
from packages.infrastructure.db.models.llm_model import LLMModel
from packages.infrastructure.db.models.llm_model_routing_settings import LLMModelRoutingSettings
from packages.infrastructure.db.models.provider import Provider


@dataclass(frozen=True)
class ModelRoutingRow:
    model: ModelProfile
    priority_weight: int


class ModelRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_routing_candidates(
        self,
        *,
        intent: Intent,
        priority: Priority,
        require_json: bool,
    ) -> list[ModelRoutingRow]:
        stmt = (
            select(LLMModel, Provider, LLMModelRoutingSettings)
            .join(Provider, Provider.id == LLMModel.provider_id)
            .join(LLMModelRoutingSettings, LLMModelRoutingSettings.model_id == LLMModel.id)
            .where(Provider.is_active.is_(True))
            .where(LLMModel.is_active.is_(True))
            .where(LLMModel.is_available.is_(True))
            .where(LLMModelRoutingSettings.enabled_for_routing.is_(True))
        )

        if require_json:
            stmt = stmt.where(LLMModel.supports_json.is_(True))

        rows = self.session.exec(stmt).all()

        mapped: list[ModelRoutingRow] = []
        for llm_model, provider, routing in rows:
            capabilities: set[Capability] = {Capability.GENERAL}
            if llm_model.supports_json:
                capabilities.add(Capability.JSON)

            model = ModelProfile(
                model_id=llm_model.routing_key,
                provider=provider.slug,
                quality_score=routing.quality_score,
                latency_score=routing.latency_score,
                cost_score=routing.cost_score,
                default_temperature=routing.default_temperature,
                capabilities=capabilities,
            )
            mapped.append(ModelRoutingRow(model=model, priority_weight=routing.priority_weight))

        _ = intent
        return self._order_for_priority(mapped, priority=priority)

    def list_all_models(self) -> list[ModelProfile]:
        stmt = (
            select(LLMModel, Provider, LLMModelRoutingSettings)
            .join(Provider, Provider.id == LLMModel.provider_id)
            .join(LLMModelRoutingSettings, LLMModelRoutingSettings.model_id == LLMModel.id, isouter=True)
            .where(Provider.is_active.is_(True))
            .where(LLMModel.is_active.is_(True))
        )
        rows = self.session.exec(stmt).all()

        models: list[ModelProfile] = []
        for llm_model, provider, routing in rows:
            capabilities: set[Capability] = {Capability.GENERAL}
            if llm_model.supports_json:
                capabilities.add(Capability.JSON)

            quality_score = routing.quality_score if routing else 0
            latency_score = routing.latency_score if routing else 0
            cost_score = routing.cost_score if routing else 0
            default_temperature = routing.default_temperature if routing else 0.2

            models.append(
                ModelProfile(
                    model_id=llm_model.routing_key,
                    provider=provider.slug,
                    quality_score=quality_score,
                    latency_score=latency_score,
                    cost_score=cost_score,
                    default_temperature=default_temperature,
                    capabilities=capabilities,
                )
            )
        return models

    def _order_for_priority(self, rows: list[ModelRoutingRow], *, priority: Priority) -> list[ModelRoutingRow]:
        _ = priority
        return sorted(rows, key=lambda row: row.priority_weight, reverse=True)

