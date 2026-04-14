from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.runners import Runner
from app.services.projects import ProjectService
from app.services.runs import RunService
from app.workers.queue import RunQueue


def get_session(request: Request) -> Iterator[Session]:
    session_factory = request.app.state.session_factory
    with session_factory() as session:
        yield session


def get_run_queue(request: Request) -> RunQueue:
    return request.app.state.run_queue


def get_runner_registry(request: Request) -> dict[str, Runner]:
    return dict(request.app.state.runner_registry)


def get_project_service(
    session: Annotated[Session, Depends(get_session)],
) -> ProjectService:
    return ProjectService(session)


def get_run_service(
    session: Annotated[Session, Depends(get_session)],
    run_queue: Annotated[RunQueue, Depends(get_run_queue)],
    runner_registry: Annotated[dict[str, Runner], Depends(get_runner_registry)],
) -> RunService:
    return RunService(
        session=session,
        run_queue=run_queue,
        runner_registry=runner_registry,
    )


ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]
RunServiceDep = Annotated[RunService, Depends(get_run_service)]
