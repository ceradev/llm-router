"""Batch catalog evaluation: heuristic for `cataloged`, live for `provisional` (v1 text→text scope)."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from sqlalchemy import or_
from sqlmodel import Session, select

from packages.infrastructure.config.settings import Settings
from packages.infrastructure.db.models.llm_model import LLMModel, ModelEvaluationStatus
from packages.infrastructure.db.models.model_benchmark_run import BenchmarkRunStatus
from packages.infrastructure.db.models.provider import Provider
from packages.infrastructure.providers.openrouter_client import OpenRouterClientError
from packages.services.benchmark.live_model_benchmark_service import LiveModelBenchmarkService
from packages.services.benchmark.model_benchmark_service import (
    ModelBenchmarkService,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CatalogEvaluationConfig:
    max_models_per_run: int = 50
    max_live_benchmarks_per_run: int = 10
    provider_allowlist: frozenset[str] | None = None
    include_verified_live: bool = False
    live_delay_seconds: float = 2.0
    enable_image_text_v2: bool = False
    strict_image_text_checks: bool = True
    enable_file_text_v3: bool = False
    strict_file_text_checks: bool = True


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
        enable_image_text_v2=settings.catalog_evaluation_enable_image_text_v2,
        strict_image_text_checks=settings.catalog_evaluation_strict_image_text_checks,
        enable_file_text_v3=settings.catalog_evaluation_enable_file_text_v3,
        strict_file_text_checks=settings.catalog_evaluation_strict_file_text_checks,
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

        rows = self._session.exec(self._heuristic_rows_stmt()).all()
        done = 0

        for model, provider in rows:
            if done >= config.max_models_per_run:
                break
            if not self._provider_ok(provider.slug, config):
                continue

            assert model.id is not None
            try:
                out = self._heuristic.run_heuristic_screening(
                    model_id=model.id,
                    enable_image_text_v2=config.enable_image_text_v2,
                    enable_file_text_v3=config.enable_file_text_v3,
                )
                done += 1
                if out.status == BenchmarkRunStatus.SKIPPED_UNSUPPORTED:
                    summary.heuristic_skipped_out_of_scope += 1
                else:
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

        rows = self._session.exec(self._live_rows_stmt(config)).all()

        providers: dict[str, list[tuple[LLMModel, Provider]]] = {}
        for model, provider in rows:
            if provider.slug not in providers:
                providers[provider.slug] = []
            providers[provider.slug].append((model, provider))

        done = 0
        for provider_slug in sorted(providers.keys()):
            if config.max_live_benchmarks_per_run > 0 and done >= config.max_live_benchmarks_per_run:
                break

            provider_models = providers[provider_slug]
            logger.info(
                "Starting live evaluation for provider '%s' with %s models (evaluated so far: %s)",
                provider_slug,
                len(provider_models),
                done,
            )

            for model, provider in provider_models:
                if config.max_live_benchmarks_per_run > 0 and done >= config.max_live_benchmarks_per_run:
                    break

                if not self._provider_ok(provider.slug, config):
                    continue

                assert model.id is not None
                out = None
                max_retries = 3
                base_delay = config.live_delay_seconds

                for attempt in range(max_retries):
                    try:
                        out = self._live.run_live_benchmark_for_model(
                            model_id=model.id,
                            enable_image_text_v2=config.enable_image_text_v2,
                            strict_image_text_checks=config.strict_image_text_checks,
                            enable_file_text_v3=config.enable_file_text_v3,
                            strict_file_text_checks=config.strict_file_text_checks,
                        )
                        break
                    except Exception as exc:
                        is_rate_limit = (
                            isinstance(exc, OpenRouterClientError) and exc.status_code in (429, 502)
                        )
                        if is_rate_limit and attempt < max_retries - 1:
                            delay = base_delay * (2 ** attempt)
                            logger.warning(
                                "catalog_eval phase=live retry for model_id=%s attempt=%s delay=%s: %s",
                                model.id,
                                attempt + 1,
                                delay,
                                exc,
                            )
                            time.sleep(delay)
                        else:
                            raise

                done += 1
                if out.status == BenchmarkRunStatus.SKIPPED_UNSUPPORTED:
                    summary.live_skipped_out_of_scope += 1
                else:
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

                if config.live_delay_seconds > 0:
                    time.sleep(config.live_delay_seconds)

            logger.info(
                "Finished provider '%s'. Total evaluated: %s",
                provider_slug,
                done,
            )

        logger.info(
            "Live evaluation completed: %s models evaluated.",
            done,
        )

    def _heuristic_rows_stmt(self):
        return (
            select(LLMModel, Provider)
            .join(Provider, Provider.id == LLMModel.provider_id)
            .where(
                LLMModel.evaluation_status.in_(
                    (ModelEvaluationStatus.CATALOGED, ModelEvaluationStatus.REJECTED)
                )
            )
            .where(LLMModel.is_active.is_(True))
            .where(Provider.is_active.is_(True))
            .order_by(LLMModel.id)
        )

    def _live_rows_stmt(self, config: CatalogEvaluationConfig):
        status_filter = self._live_status_filter(config)
        return (
            select(LLMModel, Provider)
            .join(Provider, Provider.id == LLMModel.provider_id)
            .where(status_filter)
            .where(LLMModel.is_active.is_(True))
            .where(Provider.is_active.is_(True))
            .order_by(Provider.slug, LLMModel.id)
        )

    def _live_status_filter(self, config: CatalogEvaluationConfig):
        if config.include_verified_live:
            return or_(
                LLMModel.evaluation_status == ModelEvaluationStatus.PROVISIONAL,
                LLMModel.evaluation_status == ModelEvaluationStatus.VERIFIED,
            )
        return LLMModel.evaluation_status == ModelEvaluationStatus.PROVISIONAL
