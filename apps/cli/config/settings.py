from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class CLISettings:
    max_alternatives: int = 2
    default_mode: str = "balanced"


def _read_positive_int(name: str, fallback: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return fallback
    try:
        parsed = int(raw)
    except ValueError:
        return fallback
    return parsed if parsed > 0 else fallback


def load_settings() -> CLISettings:
    return CLISettings(
        max_alternatives=_read_positive_int("LLM_ROUTER_CLI_MAX_ALTERNATIVES", 2),
        default_mode=os.getenv("LLM_ROUTER_CLI_DEFAULT_MODE", "balanced"),
    )
