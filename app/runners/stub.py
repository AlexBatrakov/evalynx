from __future__ import annotations

from app.db.models import Run
from app.runners.base import RunnerExecutionError, RunnerResult


class StubRunner:
    runner_type = "stub"

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
