from __future__ import annotations

from packages.core.scoring.engine import compute_model_score
from packages.domain.gateway import GatewayTask, Intent, Priority, RoutingDecision
from packages.domain.models import ModelProfile
from packages.infrastructure.db.repositories.model_repository import ModelRepository, ModelRoutingRow


class ModelSelector:
    def __init__(self, *, model_repository: ModelRepository, fallback_registry) -> None:
        self.model_repository = model_repository
        self.fallback_registry = fallback_registry

    def build_decision(self, *, task: GatewayTask, intent: Intent) -> RoutingDecision:
        db_rows = self._load_candidates(intent=intent, priority=task.priority, require_json=task.require_json)
        candidates = self._rank_candidates(rows=db_rows, priority=task.priority)

        if not candidates:
            candidates = [
                model
                for model in self.fallback_registry.list_models()
                if not task.require_json or model.supports_json
            ]

        if not candidates:
            raise RuntimeError("No eligible models available for routing")

        temperature = task.temperature
        if temperature is None:
            temperature = self._default_temperature(intent, candidates[0])

        reason = self._build_reason(
            intent=intent,
            priority=task.priority,
            primary_model=candidates[0].model_id,
            require_json=task.require_json,
            ranked=candidates,
            db_rows=db_rows,
        )

        return RoutingDecision(
            intent=intent,
            reason=reason,
            applied_temperature=temperature,
            candidates=candidates,
        )

    def _load_candidates(
        self,
        *,
        intent: Intent,
        priority: Priority,
        require_json: bool,
    ) -> list[ModelRoutingRow]:
        return self.model_repository.list_routing_candidates(intent=intent, priority=priority, require_json=require_json)

    def _rank_candidates(self, *, rows: list[ModelRoutingRow], priority: Priority) -> list[ModelProfile]:
        scored: list[tuple[float, ModelProfile]] = []
        for row in rows:
            breakdown = compute_model_score(
                model=row.model,
                priority=priority,
                priority_weight=row.priority_weight,
            )
            scored.append((breakdown.total, row.model))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [model for _, model in scored]

    def _default_temperature(self, intent: Intent, primary_model: ModelProfile) -> float:
        if intent == Intent.CODE:
            return 0.1
        if intent == Intent.CREATIVE:
            return 0.8
        if intent == Intent.ANALYSIS:
            return 0.2
        return primary_model.default_temperature

    def _build_reason(
        self,
        *,
        intent: Intent,
        priority: Priority,
        primary_model: str,
        require_json: bool,
        ranked: list[ModelProfile],
        db_rows: list[ModelRoutingRow],
    ) -> str:
        reason = (
            f"Intent detected: {intent.value}. Priority: {priority.value}. "
            f"Primary candidate: {primary_model}."
        )
        if require_json:
            reason += " JSON-capable models only."

        top = ranked[:3]
        if top:
            reason += " Ranked: " + ", ".join(model.model_id for model in top) + "."

        if db_rows:
            top_map = {row.model.model_id: row for row in db_rows}
            snippets: list[str] = []
            for model in top:
                row = top_map.get(model.model_id)
                if not row:
                    continue
                snippets.append(
                    compute_model_score(
                        model=row.model,
                        priority=priority,
                        priority_weight=row.priority_weight,
                    ).explanation
                )
            if snippets:
                reason += " " + " | ".join(snippets)
        return reason

