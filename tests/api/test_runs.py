from __future__ import annotations

from fastapi.testclient import TestClient

from tests.support import ManualRunQueue


def _create_project(client: TestClient) -> int:
    response = client.post("/projects", json={"name": "Packet 05 Project"})
    assert response.status_code == 201
    return response.json()["id"]


def _assert_attempt_snapshot(
    attempt: dict[str, object],
    *,
    attempt_number: int,
    status: str,
) -> None:
    assert attempt["attempt_number"] == attempt_number
    assert attempt["status"] == status


def test_create_run_returns_attempt_aware_detail_and_lists_through_api(
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
                "zeta": 3,
                "alpha": {"delta": 2, "beta": 1},
            },
        },
    )

    assert create_response.status_code == 201
    run = create_response.json()
    assert run["project_id"] == project_id
    assert run["status"] == "queued"
    assert run["current_attempt_number"] == 1
    assert run["attempt_count"] == 1
    assert run["submitted_config"] == {
        "zeta": 3,
        "alpha": {"delta": 2, "beta": 1},
    }
    assert run["normalized_config"] == {
        "alpha": {"beta": 1, "delta": 2},
        "zeta": 3,
    }
    assert len(run["config_hash"]) == 64
    assert run["summary"] is None
    assert run["result_metrics"] is None
    assert run["result_execution"] is None
    assert run["result_artifacts"] is None
    assert run["result_warnings"] is None
    assert run["result_error"] is None
    assert run["failure_message"] is None
    assert len(run["attempts"]) == 1
    _assert_attempt_snapshot(run["attempts"][0], attempt_number=1, status="queued")
    assert run_queue.pending_attempt_ids == [run["attempts"][0]["id"]]

    all_runs_response = client.get("/runs")
    assert all_runs_response.status_code == 200
    listed_run = all_runs_response.json()[0]
    assert "attempts" not in listed_run
    assert listed_run["id"] == run["id"]
    assert listed_run["attempt_count"] == 1
    assert listed_run["current_attempt_number"] == 1

    get_run_response = client.get(f"/runs/{run['id']}")
    assert get_run_response.status_code == 200
    assert get_run_response.json() == run

    project_runs_response = client.get(f"/projects/{project_id}/runs")
    assert project_runs_response.status_code == 200
    project_run = project_runs_response.json()[0]
    assert "attempts" not in project_run
    assert project_run["id"] == run["id"]
    assert project_run["attempt_count"] == 1


def test_create_run_requires_existing_project(client: TestClient) -> None:
    response = client.post(
        "/runs",
        json={
            "project_id": 999,
            "runner_type": "stub",
            "config": {},
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Project 999 was not found."}


def test_create_run_rejects_unknown_runner(client: TestClient) -> None:
    project_id = _create_project(client)

    response = client.post(
        "/runs",
        json={
            "project_id": project_id,
            "runner_type": "unknown-runner",
            "config": {},
        },
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Runner type 'unknown-runner' is not supported. Supported runners: solo_wargame, stub."
    }


def test_retry_run_requeues_failed_run_with_new_attempt(
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
                "failure_message": "retry me",
            },
        },
    )
    assert create_response.status_code == 201

    first_attempt_id = create_response.json()["attempts"][0]["id"]
    assert run_queue.run_all() == [first_attempt_id]

    retry_response = client.post(f"/runs/{create_response.json()['id']}/retry")
    assert retry_response.status_code == 200
    retried_run = retry_response.json()
    assert retried_run["status"] == "queued"
    assert retried_run["current_attempt_number"] == 2
    assert retried_run["attempt_count"] == 2
    assert retried_run["summary"] is None
    assert retried_run["failure_message"] is None
    assert retried_run["result_error"] is None
    assert retried_run["started_at"] is None
    assert retried_run["finished_at"] is None
    assert len(retried_run["attempts"]) == 2
    _assert_attempt_snapshot(retried_run["attempts"][0], attempt_number=1, status="failed")
    _assert_attempt_snapshot(retried_run["attempts"][1], attempt_number=2, status="queued")
    assert retried_run["attempts"][0]["failure_message"] == "retry me"
    assert run_queue.pending_attempt_ids == [retried_run["attempts"][1]["id"]]


def test_retry_run_rejects_non_failed_state(
    client: TestClient,
) -> None:
    project_id = _create_project(client)
    create_response = client.post(
        "/runs",
        json={
            "project_id": project_id,
            "runner_type": "stub",
            "config": {},
        },
    )
    assert create_response.status_code == 201

    response = client.post(f"/runs/{create_response.json()['id']}/retry")

    assert response.status_code == 409
    assert response.json() == {
        "detail": f"Run {create_response.json()['id']} can only be retried from failed state."
    }


def test_retry_run_returns_not_found_for_missing_run(client: TestClient) -> None:
    response = client.post("/runs/404/retry")

    assert response.status_code == 404
    assert response.json() == {"detail": "Run 404 was not found."}


def test_project_runs_returns_not_found_for_missing_project(client: TestClient) -> None:
    response = client.get("/projects/404/runs")

    assert response.status_code == 404
    assert response.json() == {"detail": "Project 404 was not found."}


def test_create_solo_wargame_run_normalizes_config_and_queues(
    client: TestClient,
    run_queue: ManualRunQueue,
) -> None:
    project_id = _create_project(client)

    response = client.post(
        "/runs",
        json={
            "project_id": project_id,
            "runner_type": "solo_wargame",
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
            },
        },
    )

    assert response.status_code == 201
    run = response.json()
    assert run["status"] == "queued"
    assert run["normalized_config"] == {
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
        "write_episode_rows": False,
    }
    assert run_queue.pending_attempt_ids == [run["attempts"][0]["id"]]


def test_create_solo_wargame_run_rejects_invalid_config(client: TestClient) -> None:
    project_id = _create_project(client)

    response = client.post(
        "/runs",
        json={
            "project_id": project_id,
            "runner_type": "solo_wargame",
            "config": {
                "mission_path": "configs/missions/missing.toml",
                "policy": {
                    "kind": "builtin",
                    "name": "heuristic",
                },
                "seed_spec": {
                    "kind": "range",
                    "start": 0,
                    "stop": 4,
                },
            },
        },
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": (
            "config.mission_path was not found in the configured solo_wargame repo: "
            "configs/missions/missing.toml"
        )
    }
