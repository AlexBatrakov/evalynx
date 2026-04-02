from __future__ import annotations

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or get_settings()

    app = FastAPI(
        title=active_settings.app_name,
        debug=active_settings.debug,
    )
    app.include_router(api_router, prefix=active_settings.api_prefix)

    if settings is not None:
        app.dependency_overrides[get_settings] = lambda: settings

    return app


app = create_app()
