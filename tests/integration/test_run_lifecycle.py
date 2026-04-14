from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Run, RunAttempt, RunStatus
from app.runners.base import RunnerResult
from app.runners.solo_wargame import RUNNER_TYPE
from tests.support import ManualRunQueue


class InspectingStubRunner:
    runner_type = "stub"

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self.observed_status: RunStatus | None = None
        self.observed_attempt_status: RunStatus | None = None

    def execute(self, run: Run, attempt: RunAttempt) -> RunnerResult:
        with self._session_factory() as session:
            persisted_run = session.get(Run, run.id)
            persisted_attempt = session.get(RunAttempt, attempt.id)
            if persisted_run is not None:
                self.observed_status = persisted_run.status
            if persisted_attempt is not None:
                self.observed_attempt_status = persisted_attempt.status

        return RunnerResult(
            summary={
                "message": "Observed running state before completion.",
                "run_id": run.id,
                "attempt_number": attempt.attempt_number,
            }
        )


class RecoveryStubRunner:
    runner_type = "stub"

    def execute(self, run: Run, attempt: RunAttempt) -> RunnerResult:
        return RunnerResult(
            summary={
                "message": "Recovered on retry.",
                "run_id": run.id,
                "attempt_number": attempt.attempt_number,
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

    processed_attempt_ids = run_queue.run_all()
    assert processed_attempt_ids == [queued_run["attempts"][0]["id"]]
    assert inspecting_runner.observed_status == RunStatus.RUNNING
    assert inspecting_runner.observed_attempt_status == RunStatus.RUNNING

    completed_response = client.get(f"/runs/{queued_run['id']}")
    assert completed_response.status_code == 200
    completed_run = completed_response.json()
    assert completed_run["status"] == "succeeded"
    assert completed_run["current_attempt_number"] == 1
    assert completed_run["attempt_count"] == 1
    assert completed_run["started_at"] is not None
    assert completed_run["finished_at"] is not None
    assert completed_run["summary"] == {
        "message": "Observed running state before completion.",
        "run_id": queued_run["id"],
        "attempt_number": 1,
    }
    assert completed_run["result_artifacts"] == []
    assert completed_run["result_warnings"] == []
    assert completed_run["result_error"] is None
    assert completed_run["attempts"][0]["status"] == "succeeded"


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

    processed_attempt_ids = run_queue.run_all()
    assert processed_attempt_ids == [queued_run["attempts"][0]["id"]]

    failed_response = client.get(f"/runs/{queued_run['id']}")
    assert failed_response.status_code == 200
    failed_run = failed_response.json()
    assert failed_run["status"] == "failed"
    assert failed_run["current_attempt_number"] == 1
    assert failed_run["attempt_count"] == 1
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
    assert failed_run["attempts"][0]["status"] == "failed"
    assert failed_run["attempts"][0]["failure_message"] == "Stub lifecycle failure."


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

    processed_attempt_ids = run_queue.run_all()
    assert processed_attempt_ids == [queued_run["attempts"][0]["id"]]

    failed_run = client.get(f"/runs/{queued_run['id']}").json()
    assert failed_run["status"] == "failed"
    assert failed_run["summary"] is None
    assert failed_run["failure_message"] == "Runner type 'stub' is not available in the worker."
    assert failed_run["result_error"] == {
        "kind": "worker_runner_missing",
        "message": "Runner type 'stub' is not available in the worker.",
    }
    assert failed_run["attempts"][0]["status"] == "failed"


def test_failed_run_retry_preserves_prior_attempt_history(
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
                "should_fail": True,
                "failure_message": "first attempt failed",
            },
        },
    )
    assert create_response.status_code == 201

    first_attempt_id = create_response.json()["attempts"][0]["id"]
    assert run_queue.run_all() == [first_attempt_id]

    retry_response = client.post(f"/runs/{create_response.json()['id']}/retry")
    assert retry_response.status_code == 200
    retried_run = retry_response.json()
    second_attempt_id = retried_run["attempts"][1]["id"]

    client.app.state.run_worker._runner_registry = {"stub": RecoveryStubRunner()}
    assert run_queue.run_all() == [second_attempt_id]

    recovered_run = client.get(f"/runs/{create_response.json()['id']}").json()
    assert recovered_run["status"] == "succeeded"
    assert recovered_run["current_attempt_number"] == 2
    assert recovered_run["attempt_count"] == 2
    assert recovered_run["summary"] == {
        "message": "Recovered on retry.",
        "run_id": create_response.json()["id"],
        "attempt_number": 2,
    }
    assert recovered_run["failure_message"] is None
    assert [attempt["attempt_number"] for attempt in recovered_run["attempts"]] == [1, 2]
    assert recovered_run["attempts"][0]["status"] == "failed"
    assert recovered_run["attempts"][0]["failure_message"] == "first attempt failed"
    assert recovered_run["attempts"][1]["status"] == "succeeded"
    assert recovered_run["attempts"][1]["summary"] == recovered_run["summary"]


def test_stale_attempt_replay_does_not_corrupt_latest_run_state(
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
                "should_fail": True,
                "failure_message": "stale failure",
            },
        },
    )
    assert create_response.status_code == 201

    first_attempt_id = create_response.json()["attempts"][0]["id"]
    assert run_queue.run_all() == [first_attempt_id]

    retry_response = client.post(f"/runs/{create_response.json()['id']}/retry")
    assert retry_response.status_code == 200
    second_attempt_id = retry_response.json()["attempts"][1]["id"]

    client.app.state.run_worker._runner_registry = {"stub": RecoveryStubRunner()}
    assert run_queue.run_all() == [second_attempt_id]

    run_queue.enqueue(first_attempt_id)
    assert run_queue.run_all() == [first_attempt_id]

    run_after_stale_replay = client.get(f"/runs/{create_response.json()['id']}").json()
    assert run_after_stale_replay["status"] == "succeeded"
    assert run_after_stale_replay["current_attempt_number"] == 2
    assert run_after_stale_replay["summary"] == {
        "message": "Recovered on retry.",
        "run_id": create_response.json()["id"],
        "attempt_number": 2,
    }
    assert run_after_stale_replay["attempts"][0]["status"] == "failed"
    assert run_after_stale_replay["attempts"][1]["status"] == "succeeded"


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

    processed_attempt_ids = run_queue.run_all()
    assert processed_attempt_ids == [create_response.json()["attempts"][0]["id"]]

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
    assert all("/attempt-0001/" in artifact["path"] for artifact in completed_run["result_artifacts"])
    assert completed_run["result_warnings"] == []
    assert completed_run["result_error"] is None
    assert completed_run["failure_message"] is None
    assert completed_run["attempts"][0]["status"] == "succeeded"


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

    processed_attempt_ids = run_queue.run_all()
    assert processed_attempt_ids == [create_response.json()["attempts"][0]["id"]]

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
    assert failed_run["attempts"][0]["status"] == "failed"
