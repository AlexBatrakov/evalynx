from __future__ import annotations

from fastapi.testclient import TestClient

from tests.support import ManualRunQueue


def _create_project(client: TestClient) -> int:
    response = client.post("/projects", json={"name": "Packet 03 Project"})
    assert response.status_code == 201
    return response.json()["id"]


def test_create_run_returns_queued_and_lists_through_api(
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
    assert run["failure_message"] is None
    assert run_queue.pending_run_ids == [run["id"]]

    all_runs_response = client.get("/runs")
    assert all_runs_response.status_code == 200
    assert all_runs_response.json() == [run]

    get_run_response = client.get(f"/runs/{run['id']}")
    assert get_run_response.status_code == 200
    assert get_run_response.json() == run

    project_runs_response = client.get(f"/projects/{project_id}/runs")
    assert project_runs_response.status_code == 200
    assert project_runs_response.json() == [run]


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
        "detail": "Runner type 'unknown-runner' is not supported. Supported runners: stub."
    }


def test_project_runs_returns_not_found_for_missing_project(client: TestClient) -> None:
    response = client.get("/projects/404/runs")

    assert response.status_code == 404
    assert response.json() == {"detail": "Project 404 was not found."}
