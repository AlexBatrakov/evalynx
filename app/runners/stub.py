from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.db.models import Run
from app.runners.base import RunnerConfigValidationError, RunnerExecutionError, RunnerResult


class StubRunner:
    runner_type = "stub"

    def normalize_config(self, config: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(config, Mapping):
            raise RunnerConfigValidationError("stub config must be an object")

        return {str(key): value for key, value in config.items()}

    def execute(self, run: Run) -> RunnerResult:
        if run.normalized_config.get("should_fail"):
            message = run.normalized_config.get("failure_message", "Stub runner configured to fail.")
            raise RunnerExecutionError(str(message))

        return RunnerResult(
            summary={
                "message": "Stub runner completed successfully.",
                "runner_type": self.runner_type,
                "project_id": run.project_id,
                "config_echo": run.normalized_config,
            }
        )
