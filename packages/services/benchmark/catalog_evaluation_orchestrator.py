"""Batch catalog evaluation: heuristic for `cataloged`, live for `provisional` (v1 text→text scope)."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from sqlalchemy import or_
from sqlmodel import Session, select

from packages.infrastructure.config.settings import Settings
from packages.infrastructure.db.models.llm_model import LLMModel, ModelEvaluationStatus
from packages.infrastructure.db.models.provider import Provider
from packages.services.benchmark.live_model_benchmark_service import LiveModelBenchmarkService
from packages.services.benchmark.model_benchmark_service import (
    ModelBenchmarkService,
    is_active_text_to_text_evaluation_scope,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CatalogEvaluationConfig:
    max_models_per_run: int = 50
    max_live_benchmarks_per_run: int = 10
    provider_allowlist: frozenset[str] | None = None
    include_verified_live: bool = False
    live_delay_seconds: float = 2.0


@dataclass
class CatalogEvaluationRunSummary:
    heuristic_attempted: int = 0
    heuristic_skipped_out_of_scope: int = 0
    heuristic_errors: int = 0
    live_attempted: int = 0
    live_skipped_out_of_scope: int = 0
    live_errors: int = 0
    errors: list[str] = field(default_factory=list)

    def log_final(self) -> None:
        logger.info(
            "Catalog evaluation run summary: heuristic_attempted=%s heuristic_skipped_out_of_scope=%s "
            "heuristic_errors=%s live_attempted=%s live_skipped_out_of_scope=%s live_errors=%s",
            self.heuristic_attempted,
            self.heuristic_skipped_out_of_scope,
            self.heuristic_errors,
            self.live_attempted,
            self.live_skipped_out_of_scope,
            self.live_errors,
        )
        if self.errors:
            for msg in self.errors:
                logger.info("Catalog evaluation error detail: %s", msg)


def catalog_evaluation_config_from_settings(settings: Settings) -> CatalogEvaluationConfig:
    raw = (settings.catalog_evaluation_provider_allowlist or "").strip()
    allow: frozenset[str] | None = None
    if raw:
        parts = {p.strip().lower() for p in raw.split(",") if p.strip()}
        if parts:
            allow = frozenset(parts)
    return CatalogEvaluationConfig(
        max_models_per_run=max(0, settings.catalog_evaluation_max_models_per_run),
        max_live_benchmarks_per_run=max(0, settings.catalog_evaluation_max_live_per_run),
        provider_allowlist=allow,
        include_verified_live=settings.catalog_evaluation_include_verified_live,
        live_delay_seconds=max(0.0, settings.catalog_evaluation_live_delay_seconds),
    )


class CatalogEvaluationOrchestrator:
    def __init__(
        self,
        session: Session,
        *,
        heuristic: ModelBenchmarkService | None = None,
        live: LiveModelBenchmarkService | None = None,
    ) -> None:
        self._session = session
        self._heuristic = heuristic or ModelBenchmarkService(session)
        self._live = live or LiveModelBenchmarkService(session)

    def run(self, config: CatalogEvaluationConfig) -> CatalogEvaluationRunSummary:
        summary = CatalogEvaluationRunSummary()
        self._run_heuristic_phase(config, summary)
        self._run_live_phase(config, summary)
        summary.log_final()
        return summary

    def _provider_ok(self, slug: str, config: CatalogEvaluationConfig) -> bool:
        if config.provider_allowlist is None:
            return True
        return slug.lower() in config.provider_allowlist

    def _run_heuristic_phase(self, config: CatalogEvaluationConfig, summary: CatalogEvaluationRunSummary) -> None:
        if config.max_models_per_run <= 0:
            return

        stmt = (
            select(LLMModel, Provider)
            .join(Provider, Provider.id == LLMModel.provider_id)
            .where(LLMModel.evaluation_status == ModelEvaluationStatus.CATALOGED)
            .where(LLMModel.is_active.is_(True))
            .where(Provider.is_active.is_(True))
            .order_by(LLMModel.id)
        )
        rows = self._session.exec(stmt).all()
        done = 0

        for model, provider in rows:
            if done >= config.max_models_per_run:
                break
            if not self._provider_ok(provider.slug, config):
                continue
            if not is_active_text_to_text_evaluation_scope(model):
                summary.heuristic_skipped_out_of_scope += 1
                logger.info(
                    "catalog_eval phase=heuristic model_id=%s routing_key=%s skipped=out_of_scope_v1",
                    model.id,
                    model.routing_key,
                )
                continue

            assert model.id is not None
            try:
                out = self._heuristic.run_heuristic_screening(model_id=model.id)
                done += 1
                summary.heuristic_attempted += 1
                logger.info(
                    "catalog_eval phase=heuristic model_id=%s routing_key=%s passed=%s status=%s "
                    "evaluation_status_after=%s",
                    model.id,
                    model.routing_key,
                    out.passed,
                    out.status.value,
                    out.evaluation_status_after.value,
                )
            except Exception as exc:
                summary.heuristic_errors += 1
                msg = f"heuristic model_id={model.id} routing_key={model.routing_key}: {exc}"
                summary.errors.append(msg)
                logger.exception("catalog_eval phase=heuristic failed for model_id=%s", model.id)

    def _run_live_phase(self, config: CatalogEvaluationConfig, summary: CatalogEvaluationRunSummary) -> None:
        if config.max_live_benchmarks_per_run <= 0:
            return

        if config.include_verified_live:
            status_filter = or_(
                LLMModel.evaluation_status == ModelEvaluationStatus.PROVISIONAL,
                LLMModel.evaluation_status == ModelEvaluationStatus.VERIFIED,
            )
        else:
            status_filter = LLMModel.evaluation_status == ModelEvaluationStatus.PROVISIONAL

        stmt = (
            select(LLMModel, Provider)
            .join(Provider, Provider.id == LLMModel.provider_id)
            .where(status_filter)
            .where(LLMModel.is_active.is_(True))
            .where(Provider.is_active.is_(True))
            .order_by(LLMModel.id)
        )
        rows = self._session.exec(stmt).all()
        done = 0

        for model, provider in rows:
            if done >= config.max_live_benchmarks_per_run:
                break
            if not self._provider_ok(provider.slug, config):
                continue
            if not is_active_text_to_text_evaluation_scope(model):
                summary.live_skipped_out_of_scope += 1
                logger.info(
                    "catalog_eval phase=live model_id=%s routing_key=%s skipped=out_of_scope_v1",
                    model.id,
                    model.routing_key,
                )
                continue

            assert model.id is not None
            try:
                out = self._live.run_live_benchmark_for_model(model_id=model.id)
                done += 1
                summary.live_attempted += 1
                logger.info(
                    "catalog_eval phase=live model_id=%s routing_key=%s passed=%s status=%s "
                    "evaluation_status_after=%s",
                    model.id,
                    model.routing_key,
                    out.passed,
                    out.status.value,
                    out.evaluation_status_after.value,
                )
            except Exception as exc:
                summary.live_errors += 1
                msg = f"live model_id={model.id} routing_key={model.routing_key}: {exc}"
                summary.errors.append(msg)
                logger.exception("catalog_eval phase=live failed for model_id=%s", model.id)

            if done < config.max_live_benchmarks_per_run and config.live_delay_seconds > 0:
                time.sleep(config.live_delay_seconds)
