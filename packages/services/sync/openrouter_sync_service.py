from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session, select

from packages.core.openrouter.pricing import compute_cost_score, parse_total_pricing
from packages.core.openrouter.tier import classify_tier, should_auto_enable_for_routing
from packages.infrastructure.config.settings import get_settings
from packages.infrastructure.db.models.llm_model import LLMModel, ModelEvaluationStatus
from packages.infrastructure.db.models.llm_model_routing_settings import LLMModelRoutingSettings
from packages.infrastructure.db.repositories.model_repository import ModelRepository
from packages.infrastructure.db.repositories.provider_repository import ProviderRepository
from packages.infrastructure.providers.openrouter_client import OpenRouterClient, OpenRouterClientError
from packages.services.benchmark.catalog_evaluation_orchestrator import (
    CatalogEvaluationOrchestrator,
    catalog_evaluation_config_from_settings,
)

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    models_processed: int
    models_created: int
    models_updated: int
    failures: list[str] = field(default_factory=list)


def _source_provider(model_id: str) -> str:
    parts = model_id.split("/", 1)
    return parts[0].strip() if parts else ""


def _external_model_suffix(model_id: str) -> str:
    parts = model_id.split("/", 1)
    return parts[1].strip() if len(parts) > 1 else parts[0].strip()


def _normalize_capabilities(raw: dict[str, Any]) -> tuple[bool, bool, bool]:
    params = raw.get("supported_parameters")
    if not isinstance(params, list):
        params = []
    params_l = {str(p).lower() for p in params}
    supports_json = "structured_outputs" in params_l
    supports_tools = "tools" in params_l

    modalities: list[str] = []
    arch = raw.get("architecture")
    if isinstance(arch, dict):
        im = arch.get("input_modalities")
        if isinstance(im, list):
            modalities = [str(x).lower() for x in im]
    supports_vision = "image" in modalities

    return supports_json, supports_tools, supports_vision


def _int_or_none(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    try:
        return int(str(value).strip())
    except ValueError:
        return None


def _float_or_none(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    s = str(value).strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _utc_from_unix_ts(value: object) -> datetime | None:
    ts = _float_or_none(value)
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None


def _str_or_none(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        s = value.strip()
        return s or None
    s = str(value).strip()
    return s or None


def _list_str_or_none(value: object) -> list[str] | None:
    if not isinstance(value, list):
        return None
    out: list[str] = []
    for item in value:
        s = _str_or_none(item)
        if s is not None:
            out.append(s)
    return out or None


def _extract_openrouter_catalog_fields(raw: dict[str, Any]) -> dict[str, Any]:
    pricing = raw.get("pricing")
    arch = raw.get("architecture")
    top_provider = raw.get("top_provider")
    if not isinstance(arch, dict):
        arch = {}
    if not isinstance(top_provider, dict):
        top_provider = {}

    is_moderated = top_provider.get("is_moderated")
    if not isinstance(is_moderated, bool):
        is_moderated = None

    prompt_price = None
    completion_price = None
    input_cache_read_price = None
    input_cache_write_price = None
    if isinstance(pricing, dict):
        prompt_price = _float_or_none(pricing.get("prompt"))
        completion_price = _float_or_none(pricing.get("completion"))
        input_cache_read_price = _float_or_none(pricing.get("input_cache_read"))
        input_cache_write_price = _float_or_none(pricing.get("input_cache_write"))

    canonical_slug = _str_or_none(raw.get("canonical_slug"))
    hugging_face_id = _str_or_none(raw.get("hugging_face_id"))
    description = _str_or_none(raw.get("description"))

    return {
        "canonical_slug": canonical_slug,
        "hugging_face_id": hugging_face_id,
        "description": description,
        "upstream_created_at": _utc_from_unix_ts(raw.get("created")),
        "modality": _str_or_none(arch.get("modality")),
        "input_modalities": _list_str_or_none(arch.get("input_modalities")),
        "output_modalities": _list_str_or_none(arch.get("output_modalities")),
        "supported_parameters": _list_str_or_none(raw.get("supported_parameters")),
        "default_parameters": raw.get("default_parameters") if isinstance(raw.get("default_parameters"), dict) else None,
        "per_request_limits": raw.get("per_request_limits") if isinstance(raw.get("per_request_limits"), dict) else None,
        "prompt_price": prompt_price,
        "completion_price": completion_price,
        "input_cache_read_price": input_cache_read_price,
        "input_cache_write_price": input_cache_write_price,
        "is_moderated": is_moderated,
        "knowledge_cutoff": _str_or_none(raw.get("knowledge_cutoff")),
        "expiration_date": _str_or_none(raw.get("expiration_date")),
        "upstream_metadata_json": dict(raw),
    }


def _apply_openrouter_catalog_fields(
    *,
    row: LLMModel,
    model_id: str,
    catalog: dict[str, Any],
) -> None:
    canonical_slug = catalog["canonical_slug"] or model_id
    row.openrouter_model_id = model_id[:255]
    row.canonical_slug = canonical_slug[:255] if canonical_slug else None
    row.hugging_face_id = catalog["hugging_face_id"][:255] if catalog["hugging_face_id"] else None
    row.description = catalog["description"]
    row.upstream_created_at = catalog["upstream_created_at"]
    row.modality = catalog["modality"][:32] if catalog["modality"] else None
    row.input_modalities = catalog["input_modalities"]
    row.output_modalities = catalog["output_modalities"]
    row.supported_parameters = catalog["supported_parameters"]
    row.default_parameters = catalog["default_parameters"]
    row.per_request_limits = catalog["per_request_limits"]
    row.prompt_price = catalog["prompt_price"]
    row.completion_price = catalog["completion_price"]
    row.input_cache_read_price = catalog["input_cache_read_price"]
    row.input_cache_write_price = catalog["input_cache_write_price"]
    row.is_moderated = catalog["is_moderated"]
    row.knowledge_cutoff = catalog["knowledge_cutoff"][:32] if catalog["knowledge_cutoff"] else None
    row.expiration_date = catalog["expiration_date"][:32] if catalog["expiration_date"] else None
    row.upstream_metadata_json = catalog["upstream_metadata_json"]


class OpenRouterSyncService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self._providers = ProviderRepository(session)
        self._models = ModelRepository(session)
        self._settings = get_settings()
        self._client = OpenRouterClient(
            base_url=self._settings.openrouter_base_url,
            timeout_seconds=self._settings.openrouter_fetch_timeout_seconds,
            http_referer=self._settings.openrouter_http_referer,
            api_key=self._settings.openrouter_api_key,
        )

    def sync_models(self) -> SyncResult:
        try:
            raw_models = self._client.fetch_models()
        except OpenRouterClientError as exc:
            logger.error("OpenRouter fetch failed: %s", exc)
            return SyncResult(
                models_processed=0,
                models_created=0,
                models_updated=0,
                failures=[str(exc)],
            )

        now = datetime.now(timezone.utc)

        created = 0
        updated = 0
        processed = 0
        failures: list[str] = []

        for raw in raw_models:
            processed += 1
            try:
                c, u = self._upsert_one(raw=raw, now=now)
                created += c
                updated += u
            except Exception as exc:
                mid = raw.get("id", "?")
                msg = f"{mid}: {exc}"
                logger.exception("OpenRouter model sync failed for %s", mid)
                failures.append(msg)

        logger.info(
            "OpenRouter sync complete: processed=%s created=%s updated=%s failures=%s",
            processed,
            created,
            updated,
            len(failures),
        )

        if self._settings.catalog_evaluation_after_openrouter_sync:
            try:
                cfg = catalog_evaluation_config_from_settings(self._settings)
                CatalogEvaluationOrchestrator(self.session).run(cfg)
            except Exception:
                logger.exception("Catalog evaluation after OpenRouter sync failed")

        return SyncResult(
            models_processed=processed,
            models_created=created,
            models_updated=updated,
            failures=failures,
        )

    def _upsert_one(self, *, raw: dict[str, Any], now: datetime) -> tuple[int, int]:
        model_id = raw.get("id")
        if not model_id or not isinstance(model_id, str):
            raise ValueError("missing model id")

        src_slug = _source_provider(model_id)
        if not src_slug:
            raise ValueError("missing upstream provider segment in model id")

        provider = self._providers.ensure_provider(slug=src_slug)
        if provider.id is None:
            raise RuntimeError(f"Provider {src_slug} must have an id after ensure")

        routing_key = f"openrouter/{model_id}"
        external_model_id = _external_model_suffix(model_id)
        display_name = str(raw.get("name") or model_id)

        pricing = raw.get("pricing")
        total_cost = parse_total_pricing(pricing)
        cost_score = compute_cost_score(total_cost)

        tier = classify_tier(source_provider=src_slug, total_cost=total_cost)

        supports_json, supports_tools, supports_vision = _normalize_capabilities(raw)

        context_window = _int_or_none(raw.get("context_length"))

        top_provider = raw.get("top_provider")
        if not isinstance(top_provider, dict):
            top_provider = {}
        max_output_tokens = _int_or_none(top_provider.get("max_completion_tokens"))
        catalog = _extract_openrouter_catalog_fields(raw)

        existing = self._models.get_llm_model_by_routing_key(routing_key)

        if existing is None:
            row = LLMModel(
                provider_id=provider.id,
                external_model_id=external_model_id[:255],
                routing_key=routing_key,
                display_name=display_name[:255],
                is_active=True,
                is_available=True,
                supports_json=supports_json,
                supports_tools=supports_tools,
                supports_vision=supports_vision,
                tier=tier,
                context_window=context_window,
                max_output_tokens=max_output_tokens,
                last_seen_at=now,
                evaluation_status=ModelEvaluationStatus.CATALOGED,
            )
            _apply_openrouter_catalog_fields(row=row, model_id=model_id, catalog=catalog)
            self.session.add(row)
            self.session.flush()

            rs = LLMModelRoutingSettings(
                model_id=row.id,
                # Synced models are cataloged, not evaluated.
                # They must not compete in routing/ranking until explicitly evaluated/curated.
                quality_score=0,
                latency_score=0,
                cost_score=cost_score,
                default_temperature=0.2,
                priority_weight=100,
                allow_fallback=True,
                enabled_for_routing=False,
                is_evaluated_for_routing=False,
                notes=None,
            )
            self.session.add(rs)
            logger.info("OpenRouter model created: %s", routing_key)
            return (1, 0)

        existing.provider_id = provider.id
        existing.external_model_id = external_model_id[:255]
        existing.display_name = display_name[:255]
        _apply_openrouter_catalog_fields(row=existing, model_id=model_id, catalog=catalog)
        existing.is_active = True
        existing.is_available = True
        existing.supports_json = supports_json
        existing.supports_tools = supports_tools
        existing.supports_vision = supports_vision
        existing.tier = tier
        existing.context_window = context_window
        existing.max_output_tokens = max_output_tokens
        existing.last_seen_at = now
        self.session.add(existing)
        self.session.flush()

        rs_stmt = select(LLMModelRoutingSettings).where(LLMModelRoutingSettings.model_id == existing.id)
        rs_row = self.session.exec(rs_stmt).first()
        if rs_row is None:
            rs_row = LLMModelRoutingSettings(
                model_id=existing.id,
                quality_score=0,
                latency_score=0,
                cost_score=cost_score,
                default_temperature=0.2,
                priority_weight=100,
                allow_fallback=True,
                enabled_for_routing=False,
                is_evaluated_for_routing=False,
            )
            self.session.add(rs_row)
        else:
            rs_row.cost_score = cost_score
            self.session.add(rs_row)

        logger.info("OpenRouter model updated: %s", routing_key)
        return (0, 1)
