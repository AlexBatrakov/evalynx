from __future__ import annotations

from fastapi.testclient import TestClient


def test_create_and_list_projects(client: TestClient) -> None:
    create_response = client.post(
        "/projects",
        json={
            "name": "Campaign Alpha",
            "description": "First packet project.",
        },
    )

    assert create_response.status_code == 201
    project = create_response.json()
    assert project["id"] > 0
    assert project["name"] == "Campaign Alpha"
    assert project["description"] == "First packet project."
    assert project["created_at"] is not None

    list_response = client.get("/projects")

    assert list_response.status_code == 200
    assert list_response.json() == [project]
