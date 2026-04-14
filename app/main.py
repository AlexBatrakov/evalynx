from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.db import create_session_factory, create_sqlalchemy_engine
from app.runners import build_runner_registry
from app.workers import BackgroundRunQueue, RunQueue, RunWorker


def create_app(
    settings: Settings | None = None,
    *,
    run_queue: RunQueue | None = None,
) -> FastAPI:
    active_settings = settings or get_settings()
    engine = create_sqlalchemy_engine(active_settings.database_url)
    session_factory = create_session_factory(engine)
    runner_registry = build_runner_registry(active_settings)
    run_worker = RunWorker(
        session_factory=session_factory,
        runner_registry=runner_registry,
    )
    active_run_queue = run_queue or BackgroundRunQueue(run_worker.process_run)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            yield
        finally:
            shutdown_queue = getattr(app.state.run_queue, "shutdown", None)
            if callable(shutdown_queue):
                shutdown_queue()
            engine.dispose()

    app = FastAPI(
        title=active_settings.app_name,
        debug=active_settings.debug,
        lifespan=lifespan,
    )
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.runner_registry = runner_registry
    app.state.run_worker = run_worker
    app.state.run_queue = active_run_queue
    app.include_router(api_router, prefix=active_settings.api_prefix)

    if settings is not None:
        app.dependency_overrides[get_settings] = lambda: settings

    return app


app = create_app()
