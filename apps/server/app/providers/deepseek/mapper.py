from __future__ import annotations

from app.catalog.types import ModelProfile
from app.gateway.types import RoutedRequest
from app.providers.base import build_demo_content


def to_provider_response_content(request: RoutedRequest, model: ModelProfile, provider_name: str) -> str:
    return build_demo_content(request, model, provider_name)
