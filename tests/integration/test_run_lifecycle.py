from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Run, RunStatus
from app.runners.solo_wargame import RUNNER_TYPE
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
    assert completed_run["result_artifacts"] == []
    assert completed_run["result_warnings"] == []
    assert completed_run["result_error"] is None


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
    assert failed_run["result_artifacts"] == []
    assert failed_run["result_warnings"] == []
    assert failed_run["result_error"] == {
        "kind": "runner_execution_error",
        "message": "Stub lifecycle failure.",
    }


def test_worker_marks_run_failed_if_runner_missing_from_worker_registry(
    client: TestClient,
    run_queue: ManualRunQueue,
) -> None:
    project_id = _create_project(client)
    create_response = client.post(
        "/runs",
        json={
            "project_id": project_id,
            "runner_type": "stub",
            "config": {"scenario": "missing-runner"},
        },
    )

    assert create_response.status_code == 201
    queued_run = create_response.json()
    assert queued_run["status"] == "queued"

    client.app.state.run_worker._runner_registry = {}

    processed_run_ids = run_queue.run_all()
    assert processed_run_ids == [queued_run["id"]]

    failed_run = client.get(f"/runs/{queued_run['id']}").json()
    assert failed_run["status"] == "failed"
    assert failed_run["summary"] is None
    assert failed_run["failure_message"] == "Runner type 'stub' is not available in the worker."
    assert failed_run["result_error"] == {
        "kind": "worker_runner_missing",
        "message": "Runner type 'stub' is not available in the worker.",
    }


def test_worker_processes_solo_wargame_success_result(
    client: TestClient,
    run_queue: ManualRunQueue,
) -> None:
    project_id = _create_project(client)
    create_response = client.post(
        "/runs",
        json={
            "project_id": project_id,
            "runner_type": RUNNER_TYPE,
            "config": {
                "mission_path": "configs/missions/mission_01_secure_the_woods_1.toml",
                "policy": {
                    "kind": "builtin",
                    "name": "heuristic",
                },
                "seed_spec": {
                    "kind": "range",
                    "start": 0,
                    "stop": 4,
                },
                "write_episode_rows": True,
            },
        },
    )

    assert create_response.status_code == 201

    processed_run_ids = run_queue.run_all()
    assert processed_run_ids == [create_response.json()["id"]]

    completed_run = client.get(f"/runs/{create_response.json()['id']}").json()
    assert completed_run["status"] == "succeeded"
    assert completed_run["summary"] == {
        "operation": "episode_batch",
        "mission_id": "mission_01_secure_the_woods_1",
        "policy_name": "heuristic",
        "agent_name": "HeuristicAgent",
        "episode_count": 4,
        "win_rate": 1.0,
    }
    assert completed_run["result_metrics"]["episode_count"] == 4
    assert completed_run["result_execution"]["mission_id"] == "mission_01_secure_the_woods_1"
    assert [artifact["kind"] for artifact in completed_run["result_artifacts"]] == [
        "request",
        "episode_rows",
        "result",
    ]
    assert completed_run["result_warnings"] == []
    assert completed_run["result_error"] is None
    assert completed_run["failure_message"] is None


def test_worker_processes_solo_wargame_failure_result(
    client: TestClient,
    run_queue: ManualRunQueue,
) -> None:
    project_id = _create_project(client)
    create_response = client.post(
        "/runs",
        json={
            "project_id": project_id,
            "runner_type": RUNNER_TYPE,
            "config": {
                "mission_path": "configs/missions/mission_03_secure_the_building.toml",
                "policy": {
                    "kind": "builtin",
                    "name": "exact_guided_heuristic",
                },
                "seed_spec": {
                    "kind": "range",
                    "start": 0,
                    "stop": 2,
                },
            },
        },
    )

    assert create_response.status_code == 201

    processed_run_ids = run_queue.run_all()
    assert processed_run_ids == [create_response.json()["id"]]

    failed_run = client.get(f"/runs/{create_response.json()['id']}").json()
    assert failed_run["status"] == "failed"
    assert failed_run["summary"] == {
        "operation": "episode_batch",
        "error_kind": "policy_resolution_error",
        "mission_id": "mission_03_secure_the_building",
    }
    assert failed_run["failure_message"] == "builtin policy 'exact_guided_heuristic' does not support this mission"
    assert failed_run["result_execution"]["mission_id"] == "mission_03_secure_the_building"
    assert [artifact["kind"] for artifact in failed_run["result_artifacts"]] == [
        "request",
        "result",
    ]
    assert failed_run["result_warnings"] == []
    assert failed_run["result_error"] == {
        "kind": "policy_resolution_error",
        "message": "builtin policy 'exact_guided_heuristic' does not support this mission",
    }
