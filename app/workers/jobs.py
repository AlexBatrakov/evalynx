from __future__ import annotations

from functools import lru_cache

from app.core.config import Settings, get_settings
from app.runtime import RuntimeResources, build_runtime_resources


@lru_cache(maxsize=1)
def _get_runtime_resources(settings: Settings) -> RuntimeResources:
    return build_runtime_resources(settings)


def process_attempt_job(attempt_id: int) -> None:
    runtime = _get_runtime_resources(get_settings())
    runtime.run_worker.process_attempt(attempt_id)
