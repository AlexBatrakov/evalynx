from __future__ import annotations

import json
import shlex
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from app.db.models import Run, RunAttempt
from app.runners.base import RunnerConfigValidationError, RunnerExecutionError, RunnerResult

RUNNER_TYPE = "solo_wargame"
RUNNER_SCHEMA_VERSION = "solo_wargame_runner_v1"
EPISODE_BATCH_OPERATION = "episode_batch"
EPISODE_BATCH_MODULE = "solo_wargame_ai.cli.episode_batch_runner"

SUPPORTED_BUILTIN_POLICIES = (
    "exact_guided_heuristic",
    "heuristic",
    "random",
)


def normalize_solo_wargame_config(
    config: Mapping[str, Any],
    *,
    repo_path: Path | None,
) -> dict[str, Any]:
    if repo_path is None:
        raise RunnerConfigValidationError("solo_wargame repo path is not configured.")

    resolved_repo_path = repo_path.resolve(strict=False)
    if not resolved_repo_path.exists() or not resolved_repo_path.is_dir():
        raise RunnerConfigValidationError(
            f"solo_wargame repo path does not exist: {resolved_repo_path}",
        )

    _reject_unknown_keys(
        config,
        allowed={"mission_path", "policy", "seed_spec", "write_episode_rows"},
        field_name="config",
    )

    mission_path_value = _require_string(config, "mission_path", parent="config")
    mission_path = _normalize_repo_relative_path(
        mission_path_value,
        repo_path=resolved_repo_path,
        field_name="config.mission_path",
    )
    if not mission_path.exists() or not mission_path.is_file():
        raise RunnerConfigValidationError(
            f"config.mission_path was not found in the configured solo_wargame repo: {mission_path_value}",
        )

    policy = _parse_policy(config.get("policy"))
    seed_spec = _parse_seed_spec(config.get("seed_spec"))
    write_episode_rows = _parse_optional_bool(
        config.get("write_episode_rows"),
        field_name="config.write_episode_rows",
        default=False,
    )

    return {
        "mission_path": mission_path.relative_to(resolved_repo_path).as_posix(),
        "policy": policy,
        "seed_spec": seed_spec,
        "write_episode_rows": write_episode_rows,
    }


def build_episode_batch_request(
    normalized_config: Mapping[str, Any],
    *,
    artifact_dir: Path,
) -> dict[str, Any]:
    return {
        "schema_version": RUNNER_SCHEMA_VERSION,
        "operation": EPISODE_BATCH_OPERATION,
        "mission_path": normalized_config["mission_path"],
        "policy": normalized_config["policy"],
        "seed_spec": normalized_config["seed_spec"],
        "artifact_dir": str(artifact_dir),
        "write_episode_rows": bool(normalized_config.get("write_episode_rows", False)),
    }


def runner_result_from_episode_batch_payload(
    payload: object,
    *,
    returncode: int,
    stderr: str,
) -> RunnerResult:
    try:
        if not isinstance(payload, Mapping):
            raise RunnerExecutionError(
                "solo_wargame runner returned a non-object JSON payload.",
                result_error={
                    "kind": "result_validation_error",
                    "message": "solo_wargame runner returned a non-object JSON payload.",
                    "returncode": returncode,
                },
            )

        schema_version = _require_string(payload, "schema_version", parent="result")
        if schema_version != RUNNER_SCHEMA_VERSION:
            raise RunnerExecutionError(
                f"solo_wargame runner returned unsupported schema_version {schema_version!r}.",
                result_error={
                    "kind": "result_validation_error",
                    "message": f"solo_wargame runner returned unsupported schema_version {schema_version!r}.",
                    "returncode": returncode,
                },
            )

        operation = _require_string(payload, "operation", parent="result")
        if operation != EPISODE_BATCH_OPERATION:
            raise RunnerExecutionError(
                f"solo_wargame runner returned unsupported operation {operation!r}.",
                result_error={
                    "kind": "result_validation_error",
                    "message": f"solo_wargame runner returned unsupported operation {operation!r}.",
                    "returncode": returncode,
                },
            )

        status = _require_string(payload, "status", parent="result")
        if status not in {"succeeded", "failed"}:
            raise RunnerExecutionError(
                f"solo_wargame runner returned unsupported status {status!r}.",
                result_error={
                    "kind": "result_validation_error",
                    "message": f"solo_wargame runner returned unsupported status {status!r}.",
                    "returncode": returncode,
                },
            )

        warnings = _parse_warning_list(payload.get("warnings"))
        mismatch_warning = _build_exit_code_warning(returncode=returncode, status=status)
        if mismatch_warning is not None:
            warnings.append(mismatch_warning)
        if stderr.strip():
            warnings.append("solo_wargame runner wrote to stderr during execution.")

        artifacts = _parse_artifacts(payload.get("artifacts"))
        execution = _parse_optional_object(payload.get("execution"), "result.execution")

        if status == "succeeded":
            metrics = _require_object(payload.get("metrics"), "result.metrics")
            return RunnerResult(
                status="succeeded",
                summary=_build_success_summary(metrics=metrics, execution=execution, operation=operation),
                result_metrics=metrics,
                result_execution=execution,
                result_artifacts=artifacts,
                result_warnings=warnings,
            )

        error = _require_object(payload.get("error"), "result.error")
        message = _require_string(error, "message", parent="result.error")
        return RunnerResult(
            status="failed",
            summary=_build_failure_summary(error=error, execution=execution, operation=operation),
            failure_message=message,
            result_execution=execution,
            result_artifacts=artifacts,
            result_warnings=warnings,
            result_error=error,
        )
    except RunnerConfigValidationError as exc:
        raise RunnerExecutionError(
            str(exc),
            result_error={
                "kind": "result_validation_error",
                "message": str(exc),
                "returncode": returncode,
            },
        ) from exc


class SoloWargameRunner:
    runner_type = RUNNER_TYPE

    def __init__(
        self,
        *,
        repo_path: Path | None,
        python_command: str,
        artifact_root: Path,
    ) -> None:
        self._repo_path = repo_path.resolve(strict=False) if repo_path is not None else None
        self._python_command = python_command
        self._artifact_root = artifact_root.resolve(strict=False)

    def normalize_config(self, config: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(config, Mapping):
            raise RunnerConfigValidationError("solo_wargame config must be an object")
        return normalize_solo_wargame_config(config, repo_path=self._repo_path)

    def execute(self, run: Run, attempt: RunAttempt) -> RunnerResult:
        if self._repo_path is None:
            raise RunnerExecutionError(
                "solo_wargame repo path is not configured.",
                result_error={
                    "kind": "runner_configuration_error",
                    "message": "solo_wargame repo path is not configured.",
                },
            )

        command_prefix = shlex.split(self._python_command)
        if not command_prefix:
            raise RunnerExecutionError(
                "solo_wargame python command is empty.",
                result_error={
                    "kind": "runner_configuration_error",
                    "message": "solo_wargame python command is empty.",
                },
            )

        artifact_dir = self._artifact_root / f"run-{run.id:06d}" / f"attempt-{attempt.attempt_number:04d}"
        request_file = artifact_dir / "evalynx-request.json"
        request_payload = build_episode_batch_request(run.normalized_config, artifact_dir=artifact_dir)

        try:
            artifact_dir.mkdir(parents=True, exist_ok=True)
            request_file.write_text(
                json.dumps(request_payload, indent=2, sort_keys=True),
                encoding="utf-8",
            )
        except OSError as exc:
            raise RunnerExecutionError(
                f"Failed to prepare solo_wargame artifacts for run {run.id} attempt {attempt.attempt_number}: {exc}",
                result_error={
                    "kind": "artifact_setup_error",
                    "message": (
                        f"Failed to prepare solo_wargame artifacts for run {run.id} "
                        f"attempt {attempt.attempt_number}: {exc}"
                    ),
                    "artifact_dir": str(artifact_dir),
                    "request_file": str(request_file),
                },
            ) from exc

        command = [
            *command_prefix,
            "-m",
            EPISODE_BATCH_MODULE,
            "--request-file",
            str(request_file),
        ]

        try:
            completed = subprocess.run(
                command,
                cwd=self._repo_path,
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError as exc:
            raise RunnerExecutionError(
                f"Failed to invoke solo_wargame runner: {exc}",
                result_error={
                    "kind": "subprocess_error",
                    "message": f"Failed to invoke solo_wargame runner: {exc}",
                    "command": command,
                    "working_directory": str(self._repo_path),
                    "request_file": str(request_file),
                },
            ) from exc

        stdout = completed.stdout.strip()
        if not stdout:
            raise RunnerExecutionError(
                "solo_wargame runner returned empty stdout.",
                result_error={
                    "kind": "result_parse_error",
                    "message": "solo_wargame runner returned empty stdout.",
                    "command": command,
                    "working_directory": str(self._repo_path),
                    "request_file": str(request_file),
                    "returncode": completed.returncode,
                    "stderr": completed.stderr.strip() or None,
                },
            )

        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise RunnerExecutionError(
                f"solo_wargame runner returned invalid JSON: {exc}",
                result_error={
                    "kind": "result_parse_error",
                    "message": f"solo_wargame runner returned invalid JSON: {exc}",
                    "command": command,
                    "working_directory": str(self._repo_path),
                    "request_file": str(request_file),
                    "returncode": completed.returncode,
                    "stderr": completed.stderr.strip() or None,
                },
            ) from exc

        return runner_result_from_episode_batch_payload(
            payload,
            returncode=completed.returncode,
            stderr=completed.stderr,
        )


def _build_success_summary(
    *,
    metrics: Mapping[str, Any],
    execution: Mapping[str, Any] | None,
    operation: str,
) -> dict[str, Any]:
    summary: dict[str, Any] = {"operation": operation}
    if execution is not None:
        mission_id = execution.get("mission_id")
        if isinstance(mission_id, str):
            summary["mission_id"] = mission_id

        policy = execution.get("policy")
        if isinstance(policy, Mapping):
            policy_name = policy.get("name")
            if isinstance(policy_name, str):
                summary["policy_name"] = policy_name

    for key in ("agent_name", "episode_count", "win_rate"):
        value = metrics.get(key)
        if value is not None:
            summary[key] = value

    return summary


def _build_failure_summary(
    *,
    error: Mapping[str, Any],
    execution: Mapping[str, Any] | None,
    operation: str,
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "operation": operation,
        "error_kind": error.get("kind"),
    }
    if execution is not None:
        mission_id = execution.get("mission_id")
        if isinstance(mission_id, str):
            summary["mission_id"] = mission_id
    return summary


def _build_exit_code_warning(*, returncode: int, status: str) -> str | None:
    if status == "succeeded" and returncode != 0:
        return f"solo_wargame runner exited with code {returncode} but reported status 'succeeded'."
    if status == "failed" and returncode not in {0, 1}:
        return f"solo_wargame runner exited with code {returncode} while reporting status 'failed'."
    return None


def _parse_policy(value: object) -> dict[str, str]:
    policy = _require_object(value, "config.policy")
    _reject_unknown_keys(policy, allowed={"kind", "name"}, field_name="config.policy")

    kind = _require_string(policy, "kind", parent="config.policy")
    if kind != "builtin":
        raise RunnerConfigValidationError("config.policy.kind must be 'builtin'")

    name = _require_string(policy, "name", parent="config.policy")
    if name not in SUPPORTED_BUILTIN_POLICIES:
        supported_names = ", ".join(repr(item) for item in SUPPORTED_BUILTIN_POLICIES)
        raise RunnerConfigValidationError(
            f"config.policy.name must be one of {supported_names}",
        )

    return {"kind": kind, "name": name}


def _parse_seed_spec(value: object) -> dict[str, Any]:
    seed_spec = _require_object(value, "config.seed_spec")
    kind = _require_string(seed_spec, "kind", parent="config.seed_spec")

    if kind == "range":
        _reject_unknown_keys(
            seed_spec,
            allowed={"kind", "start", "stop"},
            field_name="config.seed_spec",
        )
        start = _require_int(seed_spec, "start", parent="config.seed_spec")
        stop = _require_int(seed_spec, "stop", parent="config.seed_spec")
        if stop <= start:
            raise RunnerConfigValidationError(
                "config.seed_spec.stop must be greater than config.seed_spec.start",
            )
        return {"kind": kind, "start": start, "stop": stop}

    if kind == "list":
        _reject_unknown_keys(
            seed_spec,
            allowed={"kind", "seeds"},
            field_name="config.seed_spec",
        )
        seeds_value = seed_spec.get("seeds")
        if not isinstance(seeds_value, list):
            raise RunnerConfigValidationError("config.seed_spec.seeds must be an array")
        seeds = [_require_plain_int(seed, field_name=f"config.seed_spec.seeds[{index}]") for index, seed in enumerate(seeds_value)]
        if not seeds:
            raise RunnerConfigValidationError("config.seed_spec.seeds must not be empty")
        return {"kind": kind, "seeds": seeds}

    raise RunnerConfigValidationError("config.seed_spec.kind must be 'range' or 'list'")


def _parse_artifacts(value: object) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise RunnerExecutionError(
            "solo_wargame runner returned a non-array artifacts payload.",
            result_error={
                "kind": "result_validation_error",
                "message": "solo_wargame runner returned a non-array artifacts payload.",
            },
        )

    artifacts: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        artifact = _require_object(item, f"result.artifacts[{index}]")
        artifacts.append(dict(artifact))
    return artifacts


def _parse_warning_list(value: object) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise RunnerExecutionError(
            "solo_wargame runner returned a non-array warnings payload.",
            result_error={
                "kind": "result_validation_error",
                "message": "solo_wargame runner returned a non-array warnings payload.",
            },
        )

    warnings: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise RunnerExecutionError(
                f"solo_wargame runner warning at index {index} was not a string.",
                result_error={
                    "kind": "result_validation_error",
                    "message": f"solo_wargame runner warning at index {index} was not a string.",
                },
            )
        warnings.append(item)
    return warnings


def _parse_optional_object(value: object, field_name: str) -> dict[str, Any] | None:
    if value is None:
        return None
    return dict(_require_object(value, field_name))


def _normalize_repo_relative_path(
    value: str,
    *,
    repo_path: Path,
    field_name: str,
) -> Path:
    candidate = Path(value).expanduser()
    resolved = candidate.resolve(strict=False) if candidate.is_absolute() else (repo_path / candidate).resolve(strict=False)
    try:
        resolved.relative_to(repo_path)
    except ValueError as exc:
        raise RunnerConfigValidationError(
            f"{field_name} must resolve inside the configured solo_wargame repo",
        ) from exc
    return resolved


def _reject_unknown_keys(
    mapping: Mapping[str, Any],
    *,
    allowed: set[str],
    field_name: str,
) -> None:
    unknown = sorted(key for key in mapping if key not in allowed)
    if unknown:
        unknown_list = ", ".join(repr(key) for key in unknown)
        raise RunnerConfigValidationError(f"{field_name} includes unsupported keys: {unknown_list}")


def _require_object(value: object, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RunnerConfigValidationError(f"{field_name} must be an object")
    return value


def _require_string(
    mapping: Mapping[str, Any],
    field_name: str,
    *,
    parent: str,
) -> str:
    value = mapping.get(field_name)
    full_name = f"{parent}.{field_name}"
    if not isinstance(value, str) or not value.strip():
        raise RunnerConfigValidationError(f"{full_name} must be a non-empty string")
    return value


def _require_int(
    mapping: Mapping[str, Any],
    field_name: str,
    *,
    parent: str,
) -> int:
    return _require_plain_int(mapping.get(field_name), field_name=f"{parent}.{field_name}")


def _require_plain_int(value: object, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise RunnerConfigValidationError(f"{field_name} must be an integer")
    return value


def _parse_optional_bool(
    value: object,
    *,
    field_name: str,
    default: bool,
) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise RunnerConfigValidationError(f"{field_name} must be a boolean")
    return value
