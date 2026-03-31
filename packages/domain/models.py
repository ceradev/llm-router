from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ModelCategory(str, Enum):
    CHAT = "chat"
    ANALYSIS = "analysis"
    CODE = "code"
    MULTIMODAL_GENERAL = "multimodal_general"
    VISION = "vision"
    OCR = "ocr"
    # Legacy values kept for compatibility during migration.
    GENERAL = "general"
    CREATIVE = "creative"
    JSON = "json"


class TechnicalCapability(str, Enum):
    JSON = "json"
    TOOLS = "tools"
    VISION = "vision"
    TEXT_INPUT = "text_input"
    TEXT_OUTPUT = "text_output"
    IMAGE_INPUT = "image_input"
    AUDIO_INPUT = "audio_input"
    AUDIO_OUTPUT = "audio_output"


class BenchmarkScope(str, Enum):
    TEXT = "text"
    CODE = "code"
    JSON_TOOLS = "json_tools"
    VISION = "vision"
    OCR = "ocr"
    IMAGE_TO_TEXT = "image_to_text"
    FILE_TO_TEXT = "file_to_text"


class Capability(str, Enum):
    """Legacy category enum kept for compatibility with existing DB/repository code."""

    GENERAL = "general"
    ANALYSIS = "analysis"
    CODE = "code"
    CREATIVE = "creative"
    JSON = "json"


@dataclass(frozen=True)
class ModelProfile:
    model_id: str
    provider: str
    quality_score: int
    latency_score: int
    cost_score: int
    default_temperature: float
    capabilities: set[Capability] = field(default_factory=set)
    model_categories: set[ModelCategory] = field(default_factory=set)
    technical_capabilities: set[TechnicalCapability] = field(default_factory=set)
    verification_scopes: set[BenchmarkScope] = field(default_factory=set)
    supports_tools: bool = False
    context_window: int | None = None
    max_output_tokens: int | None = None
    # Catalog tier from sync (e.g. free, premium, alternative).
    tier: str = "alternative"
    # Catalog evaluation + modalities (aligned with LLMModel / ModelEvaluationStatus values).
    evaluation_status: str = "cataloged"
    supports_vision: bool = False
    input_modalities: tuple[str, ...] = ()
    output_modalities: tuple[str, ...] = ()
    prompt_price: float | None = None
    completion_price: float | None = None

    @property
    def supports_json(self) -> bool:
        return (
            Capability.JSON in self.capabilities
            or TechnicalCapability.JSON in self.technical_capabilities
        )

