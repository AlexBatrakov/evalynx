from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.runners import RunnerConfigValidationError
from app.db.models import Run, RunAttempt
from app.runners.base import RunnerExecutionError
from app.runners.solo_wargame import (
    SoloWargameRunner,
    build_episode_batch_request,
    normalize_solo_wargame_config,
    runner_result_from_episode_batch_payload,
)


def _load_fixture(name: str) -> object:
    fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "solo_wargame" / name
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def test_normalize_solo_wargame_config_and_request_payload(settings) -> None:
    normalized = normalize_solo_wargame_config(
        {
            "mission_path": str(
                settings.solo_wargame_repo_path / "configs" / "missions" / "mission_01_secure_the_woods_1.toml"
            ),
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
        repo_path=settings.solo_wargame_repo_path,
    )

    assert normalized == {
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
    }

    request_payload = build_episode_batch_request(
        normalized,
        artifact_dir=Path("/tmp/evalynx-run"),
    )
    assert request_payload == {
        "schema_version": "solo_wargame_runner_v1",
        "operation": "episode_batch",
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
        "artifact_dir": "/tmp/evalynx-run",
        "write_episode_rows": True,
    }


def test_runner_result_from_success_payload_maps_structured_fields() -> None:
    result = runner_result_from_episode_batch_payload(
        _load_fixture("success_result.json"),
        returncode=0,
        stderr="",
    )

    assert result.status == "succeeded"
    assert result.summary == {
        "operation": "episode_batch",
        "mission_id": "mission_01_secure_the_woods_1",
        "policy_name": "heuristic",
        "agent_name": "HeuristicAgent",
        "episode_count": 4,
        "win_rate": 0.75,
    }
    assert result.result_metrics["episode_count"] == 4
    assert result.result_execution["mission_id"] == "mission_01_secure_the_woods_1"
    assert [artifact["kind"] for artifact in result.result_artifacts] == [
        "request",
        "episode_rows",
        "result",
    ]
    assert result.result_warnings == []
    assert result.result_error is None


def test_runner_result_from_failure_payload_maps_structured_fields() -> None:
    result = runner_result_from_episode_batch_payload(
        _load_fixture("failure_result.json"),
        returncode=1,
        stderr="",
    )

    assert result.status == "failed"
    assert result.summary == {
        "operation": "episode_batch",
        "error_kind": "policy_resolution_error",
        "mission_id": "mission_03_secure_the_building",
    }
    assert result.failure_message == (
        "builtin policy 'exact_guided_heuristic' does not support mission "
        "'mission_03_secure_the_building'; supported missions: "
        "'mission_01_secure_the_woods_1', 'mission_02_secure_the_woods_2'"
    )
    assert result.result_execution["mission_id"] == "mission_03_secure_the_building"
    assert [artifact["kind"] for artifact in result.result_artifacts] == [
        "request",
        "result",
    ]
    assert result.result_error["kind"] == "policy_resolution_error"


def test_execute_raises_parse_error_for_invalid_json(settings) -> None:
    runner = SoloWargameRunner(
        repo_path=settings.solo_wargame_repo_path,
        python_command=settings.solo_wargame_python_command,
        artifact_root=settings.artifact_root,
    )
    run = Run(
        id=7,
        project_id=1,
        runner_type="solo_wargame",
        submitted_config={},
        normalized_config={
            "mission_path": "configs/missions/malformed_output.toml",
            "policy": {
                "kind": "builtin",
                "name": "heuristic",
            },
            "seed_spec": {
                "kind": "range",
                "start": 0,
                "stop": 1,
            },
            "write_episode_rows": False,
        },
        config_hash="hash",
    )
    attempt = RunAttempt(
        id=11,
        run_id=7,
        attempt_number=2,
    )

    with pytest.raises(RunnerExecutionError) as exc_info:
        runner.execute(run, attempt)

    assert exc_info.value.result_error["kind"] == "result_parse_error"
    assert exc_info.value.result_error["message"].startswith("solo_wargame runner returned invalid JSON:")
    assert exc_info.value.result_error["command"] == [
        settings.solo_wargame_python_command,
        "-m",
        "solo_wargame_ai.cli.episode_batch_runner",
        "--request-file",
        str(settings.artifact_root / "run-000007" / "attempt-0002" / "evalynx-request.json"),
    ]
    assert exc_info.value.result_error["working_directory"] == str(settings.solo_wargame_repo_path)
    assert exc_info.value.result_error["request_file"] == str(
        settings.artifact_root / "run-000007" / "attempt-0002" / "evalynx-request.json"
    )
    assert exc_info.value.result_error["returncode"] == 0
    assert exc_info.value.result_error["stderr"] is None


def test_normalize_config_requires_configured_repo_path() -> None:
    with pytest.raises(RunnerConfigValidationError) as exc_info:
        normalize_solo_wargame_config(
            {
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
            repo_path=None,
        )

    assert str(exc_info.value) == "solo_wargame repo path is not configured."
