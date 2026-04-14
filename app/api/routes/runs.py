from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import RunServiceDep
from app.schemas.runs import RunCreate, RunRead, RunSummaryRead
from app.services.errors import (
    ProjectNotFoundError,
    RunConfigValidationError,
    RunNotFoundError,
    RunRetryNotAllowedError,
    UnsupportedRunnerError,
)

router = APIRouter(tags=["runs"])


@router.post("/runs", response_model=RunRead, status_code=status.HTTP_201_CREATED)
def create_run(
    payload: RunCreate,
    service: RunServiceDep,
) -> RunRead:
    try:
        run = service.create_run(payload)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RunConfigValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except UnsupportedRunnerError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

    return RunRead.model_validate(run)


@router.post("/runs/{run_id}/retry", response_model=RunRead)
def retry_run(
    run_id: int,
    service: RunServiceDep,
) -> RunRead:
    try:
        run = service.retry_run(run_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RunRetryNotAllowedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return RunRead.model_validate(run)


@router.get("/runs", response_model=list[RunSummaryRead])
def list_runs(service: RunServiceDep) -> list[RunSummaryRead]:
    return [RunSummaryRead.model_validate(run) for run in service.list_runs()]


@router.get("/runs/{run_id}", response_model=RunRead)
def get_run(
    run_id: int,
    service: RunServiceDep,
) -> RunRead:
    try:
        run = service.get_run(run_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return RunRead.model_validate(run)


@router.get("/projects/{project_id}/runs", response_model=list[RunSummaryRead])
def list_project_runs(
    project_id: int,
    service: RunServiceDep,
) -> list[RunSummaryRead]:
    try:
        runs = service.list_project_runs(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return [RunSummaryRead.model_validate(run) for run in runs]
