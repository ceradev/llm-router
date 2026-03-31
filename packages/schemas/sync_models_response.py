from __future__ import annotations

from pydantic import BaseModel, Field


class SyncModelsResponse(BaseModel):
    models_processed: int = Field(ge=0)
    models_created: int = Field(ge=0)
    models_updated: int = Field(ge=0)
