from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Run, RunStatus
from app.runners.base import RunnerResult
from tests.support import ManualRunQueue


class InspectingStubRunner:
    runner_type = "stub"

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self.observed_status: RunStatus | None = None

    def execute(self, run: Run) -> RunnerResult:
        with self._session_factory() as session:
            persisted_run = session.get(Run, run.id)
            if persisted_run is not None:
                self.observed_status = persisted_run.status

        return RunnerResult(
            summary={
                "message": "Observed running state before completion.",
                "run_id": run.id,
            }
        )


def _create_project(client: TestClient) -> int:
    response = client.post("/projects", json={"name": "Lifecycle Project"})
    assert response.status_code == 201
    return response.json()["id"]


def test_worker_moves_run_from_queued_to_running_to_succeeded(
    client: TestClient,
    run_queue: ManualRunQueue,
) -> None:
    project_id = _create_project(client)
    create_response = client.post(
        "/runs",
        json={
            "project_id": project_id,
            "runner_type": "stub",
            "config": {"scenario": "success"},
        },
    )

    assert create_response.status_code == 201
    queued_run = create_response.json()
    assert queued_run["status"] == "queued"

    inspecting_runner = InspectingStubRunner(client.app.state.session_factory)
    client.app.state.run_worker._runner_registry = {"stub": inspecting_runner}

    processed_run_ids = run_queue.run_all()
    assert processed_run_ids == [queued_run["id"]]
    assert inspecting_runner.observed_status == RunStatus.RUNNING

    completed_response = client.get(f"/runs/{queued_run['id']}")
    assert completed_response.status_code == 200
    completed_run = completed_response.json()
    assert completed_run["status"] == "succeeded"
    assert completed_run["started_at"] is not None
    assert completed_run["finished_at"] is not None
    assert completed_run["summary"] == {
        "message": "Observed running state before completion.",
        "run_id": queued_run["id"],
    }


def test_worker_persists_failed_terminal_state(
    client: TestClient,
    run_queue: ManualRunQueue,
) -> None:
    project_id = _create_project(client)
    create_response = client.post(
        "/runs",
        json={
            "project_id": project_id,
            "runner_type": "stub",
            "config": {
                "scenario": "failure",
                "should_fail": True,
                "failure_message": "Stub lifecycle failure.",
            },
        },
    )

    assert create_response.status_code == 201
    queued_run = create_response.json()
    assert queued_run["status"] == "queued"

    processed_run_ids = run_queue.run_all()
    assert processed_run_ids == [queued_run["id"]]

    failed_response = client.get(f"/runs/{queued_run['id']}")
    assert failed_response.status_code == 200
    failed_run = failed_response.json()
    assert failed_run["status"] == "failed"
    assert failed_run["started_at"] is not None
    assert failed_run["finished_at"] is not None
    assert failed_run["summary"] is None
    assert failed_run["failure_message"] == "Stub lifecycle failure."
