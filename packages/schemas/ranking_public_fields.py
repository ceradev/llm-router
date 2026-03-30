from __future__ import annotations

from packages.domain.models import BenchmarkScope, Capability, ModelCategory, ModelProfile, TechnicalCapability


def public_status_fields(evaluation_status: str) -> tuple[bool, str | None]:
    """Map catalog evaluation_status to UI-safe badge key. Rejected has no primary badge."""
    normalized = evaluation_status.strip().lower()
    if normalized == "verified":
        return (True, "verified")
    if normalized == "provisional":
        return (False, "provisional")
    if normalized == "cataloged":
        return (False, "available")
    if normalized == "deprecated":
        return (False, "deprecated")
    if normalized == "rejected":
        return (False, None)
    return (False, None)


def compute_model_type_labels(model: ModelProfile) -> list[str]:
    """Derive stable public labels for gateway ranking rows (single source of truth)."""
    caps = model.capabilities
    distinct_modalities = set(model.input_modalities) | set(model.output_modalities)
    multimodal = len(distinct_modalities) > 1 or model.supports_vision
    vision = model.supports_vision

    labels: list[str] = []
    if multimodal:
        labels.append("multimodal")
    if vision:
        labels.append("vision")
    if Capability.GENERAL in caps and not multimodal:
        labels.append("chat")
    if Capability.CODE in caps:
        labels.append("code")
    if Capability.ANALYSIS in caps:
        labels.append("analysis")
    if model.supports_json:
        labels.append("json")
    if model.supports_tools:
        labels.append("tools")

    seen: set[str] = set()
    out: list[str] = []
    for item in labels:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def compute_model_categories(model: ModelProfile) -> list[str]:
    categories: set[str] = {item.value for item in model.model_categories}

    # Legacy compatibility from existing capability semantics.
    if Capability.GENERAL in model.capabilities:
        categories.add(ModelCategory.CHAT.value)
    if Capability.ANALYSIS in model.capabilities:
        categories.add(ModelCategory.ANALYSIS.value)
    if Capability.CODE in model.capabilities:
        categories.add(ModelCategory.CODE.value)
    if Capability.CREATIVE in model.capabilities:
        categories.add(ModelCategory.MULTIMODAL_GENERAL.value)

    if model.supports_vision:
        categories.add(ModelCategory.VISION.value)

    distinct_modalities = set(model.input_modalities) | set(model.output_modalities)
    if len(distinct_modalities) > 1:
        categories.add(ModelCategory.MULTIMODAL_GENERAL.value)

    return sorted(categories)


def compute_technical_capabilities(model: ModelProfile) -> list[str]:
    technical: set[str] = {item.value for item in model.technical_capabilities}

    if model.supports_json:
        technical.add(TechnicalCapability.JSON.value)
    if model.supports_tools:
        technical.add(TechnicalCapability.TOOLS.value)
    if model.supports_vision:
        technical.add(TechnicalCapability.VISION.value)
    if model.input_modalities:
        if "text" in model.input_modalities:
            technical.add(TechnicalCapability.TEXT_INPUT.value)
        if "image" in model.input_modalities:
            technical.add(TechnicalCapability.IMAGE_INPUT.value)
        if "audio" in model.input_modalities:
            technical.add(TechnicalCapability.AUDIO_INPUT.value)
    if model.output_modalities:
        if "text" in model.output_modalities:
            technical.add(TechnicalCapability.TEXT_OUTPUT.value)
        if "audio" in model.output_modalities:
            technical.add(TechnicalCapability.AUDIO_OUTPUT.value)

    return sorted(technical)


def compute_verification_scopes(model: ModelProfile) -> list[str]:
    scopes = {scope.value for scope in model.verification_scopes}
    if not scopes:
        scopes.add(BenchmarkScope.TEXT.value)
    return sorted(scopes)
