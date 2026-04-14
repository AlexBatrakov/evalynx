from __future__ import annotations

import pytest
from fastapi import FastAPI

from app.schemas.projects import ProjectCreate
from app.schemas.runs import RunCreate
from app.services.errors import RunRetryNotAllowedError
from app.services.projects import ProjectService
from app.services.runs import RunService
from tests.support import ManualRunQueue


def _create_project(app: FastAPI) -> int:
    with app.state.session_factory() as session:
        project = ProjectService(session).create_project(ProjectCreate(name="Service Layer Project"))
        return project.id


def test_retry_run_requires_failed_state(app: FastAPI, run_queue: ManualRunQueue) -> None:
    project_id = _create_project(app)

    with app.state.session_factory() as session:
        service = RunService(
            session=session,
            run_queue=run_queue,
            runner_registry=app.state.runner_registry,
        )
        run = service.create_run(
            RunCreate(
                project_id=project_id,
                runner_type="stub",
                config={},
            )
        )

        with pytest.raises(RunRetryNotAllowedError) as exc_info:
            service.retry_run(run.id)

    assert str(exc_info.value) == f"Run {run.id} can only be retried from failed state."


def test_retry_run_creates_fresh_attempt_and_resets_current_snapshot(
    app: FastAPI,
    run_queue: ManualRunQueue,
) -> None:
    project_id = _create_project(app)

    with app.state.session_factory() as session:
        service = RunService(
            session=session,
            run_queue=run_queue,
            runner_registry=app.state.runner_registry,
        )
        run = service.create_run(
            RunCreate(
                project_id=project_id,
                runner_type="stub",
                config={
                    "should_fail": True,
                    "failure_message": "service retry failure",
                },
            )
        )
        first_attempt_id = run.attempts[0].id

    assert run_queue.run_all() == [first_attempt_id]

    with app.state.session_factory() as session:
        service = RunService(
            session=session,
            run_queue=run_queue,
            runner_registry=app.state.runner_registry,
        )
        retried_run = service.retry_run(run.id)

        assert retried_run.status.value == "queued"
        assert retried_run.current_attempt_number == 2
        assert retried_run.attempt_count == 2
        assert retried_run.summary is None
        assert retried_run.failure_message is None
        assert retried_run.result_error is None
        assert retried_run.started_at is None
        assert retried_run.finished_at is None
        assert retried_run.attempts[0].status.value == "failed"
        assert retried_run.attempts[0].failure_message == "service retry failure"
        assert retried_run.attempts[1].status.value == "queued"

    assert run_queue.pending_attempt_ids == [retried_run.attempts[1].id]
