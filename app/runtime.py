from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.db import create_session_factory, create_sqlalchemy_engine
from app.runners import Runner, build_runner_registry
from app.workers.run_worker import RunWorker


@dataclass(slots=True)
class RuntimeResources:
    engine: Engine
    session_factory: sessionmaker[Session]
    runner_registry: dict[str, Runner]
    run_worker: RunWorker


def build_runtime_resources(settings: Settings) -> RuntimeResources:
    engine = create_sqlalchemy_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    runner_registry = build_runner_registry(settings)
    run_worker = RunWorker(
        session_factory=session_factory,
        runner_registry=runner_registry,
    )
    return RuntimeResources(
        engine=engine,
        session_factory=session_factory,
        runner_registry=runner_registry,
        run_worker=run_worker,
    )
