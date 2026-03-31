from __future__ import annotations

from pydantic import BaseModel, Field


class ProviderResponse(BaseModel):
    id: int = Field(ge=1)
    slug: str
    display_name: str
    is_active: bool
