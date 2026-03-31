from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.exc import OperationalError
from sqlmodel import Session, select

from packages.domain.gateway import Priority
from packages.domain.models import BenchmarkScope, Capability, ModelProfile
from sqlalchemy import delete

from packages.infrastructure.db.models.llm_model import LLMModel, ModelEvaluationStatus
from packages.infrastructure.db.models.model_benchmark_run import BenchmarkKind, ModelBenchmarkRun
from packages.infrastructure.db.models.llm_model_capability import LLMModelCapability
from packages.infrastructure.db.models.llm_model_routing_settings import LLMModelRoutingSettings
from packages.infrastructure.db.models.provider import Provider
from packages.infrastructure.db.seed_types import SeededModelUpsertParams


def _modalities_tuple(raw: list[str] | None) -> tuple[str, ...]:
    if not raw:
        return ()
    return tuple(str(x).strip().lower() for x in raw if str(x).strip())


@dataclass(frozen=True)
class ModelRoutingRow:
    model: ModelProfile
    priority_weight: int
    db_model_id: int


@dataclass(frozen=True)
class AdminModelRow:
    llm_model: LLMModel
    provider: Provider


def _count_scalar(result: object) -> int:
    """exec().one() for COUNT may return a bare int or a row/tuple depending on SQLAlchemy/SQLModel version."""
    if isinstance(result, int):
        return result
    return int(result[0])


class ModelRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _capabilities_for_model(self, *, llm_model: LLMModel, extra_caps: dict[int, set[Capability]]) -> set[Capability]:
        capabilities: set[Capability] = {Capability.GENERAL}
        if llm_model.supports_json:
            capabilities.add(Capability.JSON)
        if llm_model.id is not None:
            capabilities |= extra_caps.get(llm_model.id, set())
        return capabilities

    def _routing_scores_or_defaults(
        self, routing: LLMModelRoutingSettings | None
    ) -> tuple[int, int, int, float]:
        if routing is None:
            return (0, 0, 0, 0.2)
        return (
            routing.quality_score,
            routing.latency_score,
            routing.cost_score,
            routing.default_temperature,
        )

    def _capability_rows_for_models(self, model_ids: list[int]) -> dict[int, set[Capability]]:
        if not model_ids:
            return {}
        stmt = select(LLMModelCapability).where(LLMModelCapability.model_id.in_(model_ids))
        rows = self.session.exec(stmt).all()
        by_mid: dict[int, set[Capability]] = {}
        for row in rows:
            mid = row.model_id
            if mid not in by_mid:
                by_mid[mid] = set()
            by_mid[mid].add(row.capability)
        return by_mid

    def _verification_scopes_by_model_ids(self, model_ids: list[int]) -> dict[int, set[BenchmarkScope]]:
        if not model_ids:
            return {}
        stmt = (
            select(
                ModelBenchmarkRun.model_id,
                ModelBenchmarkRun.benchmark_scope,
                func.max(ModelBenchmarkRun.id).label("max_id"),
            )
            .where(ModelBenchmarkRun.model_id.in_(model_ids))
            .where(ModelBenchmarkRun.benchmark_kind == BenchmarkKind.LIVE.value)
            .group_by(ModelBenchmarkRun.model_id, ModelBenchmarkRun.benchmark_scope)
        )
        try:
            rows = self.session.exec(stmt).all()
        except OperationalError:
            return {}
        scopes: dict[int, set[BenchmarkScope]] = {}
        for model_id, scope_str, _max_id in rows:
            try:
                scope = BenchmarkScope(str(scope_str))
            except ValueError:
                continue
            scopes.setdefault(int(model_id), set()).add(scope)
        return scopes

    def list_routing_candidates(
        self,
        *,
        priority: Priority,
        require_json: bool,
        provider_slugs: list[str] | None = None,
    ) -> list[ModelRoutingRow]:
        stmt = (
            select(LLMModel, Provider, LLMModelRoutingSettings)
            .join(Provider, Provider.id == LLMModel.provider_id)
            .join(LLMModelRoutingSettings, LLMModelRoutingSettings.model_id == LLMModel.id)
            .where(Provider.is_active.is_(True))
            .where(LLMModel.is_active.is_(True))
            .where(LLMModel.is_available.is_(True))
            .where(LLMModelRoutingSettings.enabled_for_routing.is_(True))
            .where(LLMModelRoutingSettings.is_evaluated_for_routing.is_(True))
            .where(
                LLMModel.evaluation_status.in_(
                    (ModelEvaluationStatus.VERIFIED, ModelEvaluationStatus.PROVISIONAL)
                )
            )
        )

        if provider_slugs:
            normalized = [str(s).strip().lower() for s in provider_slugs if str(s).strip()]
            if normalized:
                stmt = stmt.where(func.lower(Provider.slug).in_(normalized))

        if require_json:
            stmt = stmt.where(LLMModel.supports_json.is_(True))

        rows = self.session.exec(stmt).all()

        model_ids = [llm_model.id for llm_model, _p, _r in rows if llm_model.id is not None]
        extra_caps = self._capability_rows_for_models([mid for mid in model_ids if mid is not None])
        verification_scopes_by_mid = self._verification_scopes_by_model_ids([mid for mid in model_ids if mid is not None])

        mapped: list[ModelRoutingRow] = []
        for llm_model, provider, routing in rows:
            if llm_model.id is None:
                continue
            capabilities: set[Capability] = {Capability.GENERAL}
            if llm_model.supports_json:
                capabilities.add(Capability.JSON)
            for cap in extra_caps.get(llm_model.id, ()):
                capabilities.add(cap)

            model = ModelProfile(
                model_id=llm_model.routing_key,
                provider=provider.slug,
                quality_score=routing.quality_score,
                latency_score=routing.latency_score,
                cost_score=routing.cost_score,
                default_temperature=routing.default_temperature,
                capabilities=capabilities,
                supports_tools=llm_model.supports_tools,
                context_window=llm_model.context_window,
                max_output_tokens=llm_model.max_output_tokens,
                tier=llm_model.tier,
                evaluation_status=llm_model.evaluation_status.value,
                supports_vision=llm_model.supports_vision,
                input_modalities=_modalities_tuple(llm_model.input_modalities),
                output_modalities=_modalities_tuple(llm_model.output_modalities),
                prompt_price=llm_model.prompt_price,
                completion_price=llm_model.completion_price,
                verification_scopes=verification_scopes_by_mid.get(llm_model.id, set()),
            )
            mapped.append(
                ModelRoutingRow(
                    model=model,
                    priority_weight=routing.priority_weight,
                    db_model_id=llm_model.id,
                )
            )

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

        model_ids = [llm_model.id for llm_model, _p, _r in rows if llm_model.id is not None]
        extra_caps = self._capability_rows_for_models([mid for mid in model_ids if mid is not None])
        verification_scopes_by_mid = self._verification_scopes_by_model_ids([mid for mid in model_ids if mid is not None])

        models: list[ModelProfile] = []
        for llm_model, provider, routing in rows:
            capabilities = self._capabilities_for_model(llm_model=llm_model, extra_caps=extra_caps)
            quality_score, latency_score, cost_score, default_temperature = self._routing_scores_or_defaults(routing)

            models.append(
                ModelProfile(
                    model_id=llm_model.routing_key,
                    provider=provider.slug,
                    quality_score=quality_score,
                    latency_score=latency_score,
                    cost_score=cost_score,
                    default_temperature=default_temperature,
                    capabilities=capabilities,
                    supports_tools=llm_model.supports_tools,
                    context_window=llm_model.context_window,
                    max_output_tokens=llm_model.max_output_tokens,
                    tier=llm_model.tier,
                    evaluation_status=llm_model.evaluation_status.value,
                    supports_vision=llm_model.supports_vision,
                    input_modalities=_modalities_tuple(llm_model.input_modalities),
                    output_modalities=_modalities_tuple(llm_model.output_modalities),
                    prompt_price=llm_model.prompt_price,
                    completion_price=llm_model.completion_price,
                    verification_scopes=verification_scopes_by_mid.get(llm_model.id, set()),
                )
            )
        return models

    def get_model_id_by_routing_key(self, routing_key: str) -> int | None:
        stmt = select(LLMModel.id).where(LLMModel.routing_key == routing_key).limit(1)
        return self.session.exec(stmt).first()

    def get_llm_model_by_routing_key(self, routing_key: str) -> LLMModel | None:
        stmt = select(LLMModel).where(LLMModel.routing_key == routing_key)
        return self.session.exec(stmt).first()

    def get_model_with_provider_by_routing_key(self, *, routing_key: str) -> AdminModelRow | None:
        stmt = (
            select(LLMModel, Provider)
            .join(Provider, Provider.id == LLMModel.provider_id)
            .where(LLMModel.routing_key == routing_key)
            .limit(1)
        )
        row = self.session.exec(stmt).first()
        if row is None:
            return None
        llm_model, provider = row
        return AdminModelRow(llm_model=llm_model, provider=provider)

    def list_models_for_admin(
        self,
        *,
        provider_slug: str | None = None,
        tier: str | None = None,
        is_available: bool | None = None,
        evaluation_status: str | None = None,
    ) -> list[AdminModelRow]:
        stmt = (
            select(LLMModel, Provider)
            .join(Provider, Provider.id == LLMModel.provider_id)
            .where(LLMModel.is_active.is_(True))
            .order_by(LLMModel.routing_key.asc())
        )
        if provider_slug:
            stmt = stmt.where(func.lower(Provider.slug) == provider_slug.strip().lower())
        if tier:
            stmt = stmt.where(func.lower(LLMModel.tier) == tier.strip().lower())
        if is_available is not None:
            stmt = stmt.where(LLMModel.is_available.is_(is_available))
        if evaluation_status:
            stmt = stmt.where(func.lower(LLMModel.evaluation_status) == evaluation_status.strip().lower())
        rows = self.session.exec(stmt).all()
        return [AdminModelRow(llm_model=llm_model, provider=provider) for llm_model, provider in rows]

    def count_llm_models(self) -> int:
        stmt = select(func.count(LLMModel.id))
        row = self.session.exec(stmt).one()
        return _count_scalar(row)

    def replace_model_capabilities(self, *, model_id: int, capabilities: set[Capability]) -> None:
        self.session.exec(delete(LLMModelCapability).where(LLMModelCapability.model_id == model_id))
        for cap in capabilities:
            self.session.add(LLMModelCapability(model_id=model_id, capability=cap))

    def upsert_seeded_model(
        self,
        *,
        provider_id: int,
        params: SeededModelUpsertParams,
    ) -> tuple[str, LLMModel]:
        routing_key = f"openrouter/{params.source_provider}/{params.external_model_id}"
        existing = self.get_llm_model_by_routing_key(routing_key)
        caps = set(params.capabilities)
        if params.supports_json:
            caps.add(Capability.JSON)

        if existing is None:
            now = datetime.now(timezone.utc)
            row = LLMModel(
                provider_id=provider_id,
                external_model_id=params.external_model_id[:255],
                routing_key=routing_key,
                display_name=params.display_name[:255],
                is_active=True,
                is_available=True,
                supports_json=params.supports_json,
                supports_tools=params.supports_tools,
                supports_vision=params.supports_vision,
                tier=params.tier,
                context_window=params.context_window,
                max_output_tokens=params.max_output_tokens,
                evaluation_status=ModelEvaluationStatus.PROVISIONAL,
                evaluation_confidence=0.85,
                last_evaluated_at=now,
                evaluation_version="seeded",
            )
            self.session.add(row)
            self.session.flush()
            self._upsert_routing_settings(
                model_id=row.id,
                quality_score=params.quality_score,
                latency_score=params.latency_score,
                cost_score=params.cost_score,
                default_temperature=params.default_temperature,
                priority_weight=params.priority_weight,
            )
            self.replace_model_capabilities(model_id=row.id, capabilities=caps)
            return ("created", row)

        existing.provider_id = provider_id
        existing.external_model_id = params.external_model_id[:255]
        existing.display_name = params.display_name[:255]
        existing.is_active = True
        existing.is_available = True
        existing.supports_json = params.supports_json
        existing.supports_tools = params.supports_tools
        existing.supports_vision = params.supports_vision
        existing.tier = params.tier
        existing.context_window = params.context_window
        existing.max_output_tokens = params.max_output_tokens
        existing.evaluation_status = ModelEvaluationStatus.PROVISIONAL
        existing.evaluation_confidence = 0.85
        existing.last_evaluated_at = datetime.now(timezone.utc)
        existing.evaluation_version = "seeded"
        self.session.add(existing)
        self.session.flush()
        self._upsert_routing_settings(
            model_id=existing.id,
            quality_score=params.quality_score,
            latency_score=params.latency_score,
            cost_score=params.cost_score,
            default_temperature=params.default_temperature,
            priority_weight=params.priority_weight,
        )
        self.replace_model_capabilities(model_id=existing.id, capabilities=caps)
        return ("updated", existing)

    def _upsert_routing_settings(
        self,
        *,
        model_id: int,
        quality_score: int,
        latency_score: int,
        cost_score: int,
        default_temperature: float,
        priority_weight: int,
    ) -> None:
        stmt = select(LLMModelRoutingSettings).where(LLMModelRoutingSettings.model_id == model_id)
        rs = self.session.exec(stmt).first()
        if rs is None:
            self.session.add(
                LLMModelRoutingSettings(
                    model_id=model_id,
                    quality_score=quality_score,
                    latency_score=latency_score,
                    cost_score=cost_score,
                    default_temperature=default_temperature,
                    priority_weight=priority_weight,
                    allow_fallback=True,
                    # Curated scores are not execution-verified; competitive routing requires
                    # `evaluation_status=verified` after a live benchmark.
                    enabled_for_routing=False,
                    is_evaluated_for_routing=False,
                    notes=None,
                )
            )
            return
        rs.quality_score = quality_score
        rs.latency_score = latency_score
        rs.cost_score = cost_score
        rs.default_temperature = default_temperature
        rs.priority_weight = priority_weight
        rs.enabled_for_routing = False
        rs.is_evaluated_for_routing = False
        self.session.add(rs)

    def count_routing_ready_models(self, *, require_json: bool = False) -> int:
        stmt = (
            select(func.count(LLMModel.id))
            .select_from(LLMModel)
            .join(Provider, Provider.id == LLMModel.provider_id)
            .join(LLMModelRoutingSettings, LLMModelRoutingSettings.model_id == LLMModel.id)
            .where(Provider.is_active.is_(True))
            .where(LLMModel.is_active.is_(True))
            .where(LLMModel.is_available.is_(True))
            .where(LLMModelRoutingSettings.enabled_for_routing.is_(True))
            .where(LLMModelRoutingSettings.is_evaluated_for_routing.is_(True))
            .where(LLMModel.evaluation_status == ModelEvaluationStatus.VERIFIED)
        )
        if require_json:
            stmt = stmt.where(LLMModel.supports_json.is_(True))
        row = self.session.exec(stmt).one()
        return _count_scalar(row)

    def _order_for_priority(self, rows: list[ModelRoutingRow], *, priority: Priority) -> list[ModelRoutingRow]:
        _ = priority
        return sorted(rows, key=lambda row: row.priority_weight, reverse=True)

