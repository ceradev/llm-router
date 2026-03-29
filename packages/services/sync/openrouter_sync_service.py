from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session, select

from packages.core.openrouter.pricing import compute_cost_score, parse_total_pricing
from packages.core.openrouter.tier import classify_tier, should_auto_enable_for_routing
from packages.infrastructure.config.settings import get_settings
from packages.infrastructure.db.models.llm_model import LLMModel
from packages.infrastructure.db.models.llm_model_routing_settings import LLMModelRoutingSettings
from packages.infrastructure.db.repositories.model_repository import ModelRepository
from packages.infrastructure.db.repositories.provider_repository import ProviderRepository
from packages.infrastructure.providers.openrouter_client import OpenRouterClient, OpenRouterClientError

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

        existing = self._models.get_llm_model_by_routing_key(routing_key)

        if existing is None:
            auto_enable = should_auto_enable_for_routing(
                cost_score=cost_score,
                supports_json=supports_json,
                supports_tools=supports_tools,
                tier=tier,
                total_cost=total_cost,
            )
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
            )
            self.session.add(row)
            self.session.flush()

            rs = LLMModelRoutingSettings(
                model_id=row.id,
                quality_score=3,
                latency_score=3,
                cost_score=cost_score,
                default_temperature=0.2,
                priority_weight=100,
                allow_fallback=True,
                enabled_for_routing=auto_enable,
                notes=None,
            )
            self.session.add(rs)
            logger.info("OpenRouter model created: %s", routing_key)
            return (1, 0)

        existing.provider_id = provider.id
        existing.external_model_id = external_model_id[:255]
        existing.display_name = display_name[:255]
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
            auto_enable = should_auto_enable_for_routing(
                cost_score=cost_score,
                supports_json=supports_json,
                supports_tools=supports_tools,
                tier=tier,
                total_cost=total_cost,
            )
            rs_row = LLMModelRoutingSettings(
                model_id=existing.id,
                quality_score=3,
                latency_score=3,
                cost_score=cost_score,
                default_temperature=0.2,
                priority_weight=100,
                allow_fallback=True,
                enabled_for_routing=auto_enable,
            )
            self.session.add(rs_row)
        else:
            rs_row.cost_score = cost_score
            self.session.add(rs_row)

        logger.info("OpenRouter model updated: %s", routing_key)
        return (0, 1)
