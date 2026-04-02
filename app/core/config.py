from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


def _get_bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    normalized = value.strip().lower()
    return normalized in {"1", "true", "yes", "on"}


def _normalize_api_prefix(value: str) -> str:
    prefix = value.strip()
    if not prefix:
        return ""

    if prefix.startswith("/"):
        return prefix.rstrip("/")

    return f"/{prefix.rstrip('/')}"


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str = "Evalynx"
    environment: str = "development"
    debug: bool = False
    api_prefix: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("EVALYNX_APP_NAME", "Evalynx"),
        environment=os.getenv("EVALYNX_ENV", "development"),
        debug=_get_bool_env("EVALYNX_DEBUG", default=False),
        api_prefix=_normalize_api_prefix(os.getenv("EVALYNX_API_PREFIX", "")),
    )
