"""SQLModel ORM models.

Importing this module registers all tables for metadata creation.
"""

from packages.infrastructure.db.models.provider import Provider
from packages.infrastructure.db.models.provider_sync_run import ProviderSyncRun
from packages.infrastructure.db.models.llm_model import LLMModel
from packages.infrastructure.db.models.llm_model_capability import LLMModelCapability
from packages.infrastructure.db.models.llm_model_routing_settings import LLMModelRoutingSettings
from packages.infrastructure.db.models.llm_request import LLMRequest
from packages.infrastructure.db.models.request_analysis import RequestAnalysis
from packages.infrastructure.db.models.model_benchmark_run import (
    BenchmarkKind,
    BenchmarkRunStatus,
    BenchmarkScope,
    ModelBenchmarkRun,
)
from packages.infrastructure.db.models.model_evaluation import ModelEvaluation
from packages.infrastructure.db.models.llm_execution import LLMExecution
from packages.infrastructure.db.models.llm_attempt import LLMAttempt
from packages.infrastructure.db.models.llm_feedback import LLMFeedback

__all__ = [
    "LLMAttempt",
    "LLMExecution",
    "LLMFeedback",
    "LLMModel",
    "LLMModelCapability",
    "LLMModelRoutingSettings",
    "LLMRequest",
    "BenchmarkKind",
    "BenchmarkRunStatus",
    "BenchmarkScope",
    "ModelBenchmarkRun",
    "ModelEvaluation",
    "Provider",
    "ProviderSyncRun",
    "RequestAnalysis",
]
