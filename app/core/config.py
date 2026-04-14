from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


def _get_bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    normalized = value.strip().lower()
    return normalized in {"1", "true", "yes", "on"}


def _get_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default

    return int(value.strip())


def _normalize_api_prefix(value: str) -> str:
    prefix = value.strip()
    if not prefix:
        return ""

    if prefix.startswith("/"):
        return prefix.rstrip("/")

    return f"/{prefix.rstrip('/')}"


def _normalize_optional_path(value: str | None) -> Path | None:
    if value is None:
        return None

    stripped = value.strip()
    if not stripped:
        return None

    return Path(stripped).expanduser().resolve(strict=False)


def _normalize_required_path(value: str) -> Path:
    return Path(value).expanduser().resolve(strict=False)


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str = "Evalynx"
    environment: str = "development"
    debug: bool = False
    api_prefix: str = ""
    database_url: str = "sqlite:///./evalynx.db"
    redis_url: str = "redis://localhost:6379/0"
    rq_queue_name: str = "evalynx-runs"
    rq_job_timeout: int = 600
    solo_wargame_repo_path: Path | None = None
    solo_wargame_python_command: str = ".venv/bin/python"
    artifact_root: Path = Path("./artifacts")


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("EVALYNX_APP_NAME", "Evalynx"),
        environment=os.getenv("EVALYNX_ENV", "development"),
        debug=_get_bool_env("EVALYNX_DEBUG", default=False),
        api_prefix=_normalize_api_prefix(os.getenv("EVALYNX_API_PREFIX", "")),
        database_url=os.getenv("EVALYNX_DATABASE_URL", "sqlite:///./evalynx.db"),
        redis_url=os.getenv("EVALYNX_REDIS_URL", "redis://localhost:6379/0"),
        rq_queue_name=os.getenv("EVALYNX_RQ_QUEUE_NAME", "evalynx-runs"),
        rq_job_timeout=_get_int_env("EVALYNX_RQ_JOB_TIMEOUT", 600),
        solo_wargame_repo_path=_normalize_optional_path(os.getenv("EVALYNX_SOLO_WARGAME_REPO_PATH")),
        solo_wargame_python_command=os.getenv("EVALYNX_SOLO_WARGAME_PYTHON_COMMAND", ".venv/bin/python"),
        artifact_root=_normalize_required_path(os.getenv("EVALYNX_ARTIFACT_ROOT", "./artifacts")),
    )
