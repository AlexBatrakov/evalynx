from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
import sys

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from tests.support import ManualRunQueue, create_fake_solo_wargame_repo


def _apply_migrations(database_url: str) -> None:
    repository_root = Path(__file__).resolve().parents[1]
    alembic_config = Config(str(repository_root / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(repository_root / "alembic"))
    alembic_config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(alembic_config, "head")


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    database_path = tmp_path / "evalynx-test.db"
    solo_wargame_repo_path = create_fake_solo_wargame_repo(tmp_path / "solo-wargame-ai")
    return Settings(
        app_name="Evalynx Test",
        environment="test",
        debug=False,
        database_url=f"sqlite:///{database_path}",
        solo_wargame_repo_path=solo_wargame_repo_path,
        solo_wargame_python_command=sys.executable,
        artifact_root=tmp_path / "artifacts",
    )


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    _apply_migrations(settings.database_url)
    application = create_app(settings)
    background_queue = application.state.run_queue
    shutdown_queue = getattr(background_queue, "shutdown", None)
    if callable(shutdown_queue):
        shutdown_queue()
    application.state.run_queue = ManualRunQueue(application.state.run_worker.process_run)
    return application


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def run_queue(app: FastAPI) -> ManualRunQueue:
    return app.state.run_queue
