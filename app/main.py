from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.runtime import build_runtime_resources
from app.workers import RunQueue, build_default_run_queue


def create_app(
    settings: Settings | None = None,
    *,
    run_queue: RunQueue | None = None,
) -> FastAPI:
    active_settings = settings or get_settings()
    runtime = build_runtime_resources(active_settings)
    active_run_queue = run_queue or build_default_run_queue(active_settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            yield
        finally:
            shutdown_queue = getattr(app.state.run_queue, "shutdown", None)
            if callable(shutdown_queue):
                shutdown_queue()
            runtime.engine.dispose()

    app = FastAPI(
        title=active_settings.app_name,
        debug=active_settings.debug,
        lifespan=lifespan,
    )
    app.state.engine = runtime.engine
    app.state.session_factory = runtime.session_factory
    app.state.runner_registry = runtime.runner_registry
    app.state.run_worker = runtime.run_worker
    app.state.run_queue = active_run_queue
    app.include_router(api_router, prefix=active_settings.api_prefix)

    if settings is not None:
        app.dependency_overrides[get_settings] = lambda: settings

    return app


app = create_app()
