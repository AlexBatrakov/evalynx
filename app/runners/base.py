from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from app.db.models import Run, RunAttempt


class RunnerExecutionError(Exception):
    def __init__(
        self,
        message: str,
        *,
        summary: dict[str, Any] | None = None,
        result_metrics: dict[str, Any] | None = None,
        result_execution: dict[str, Any] | None = None,
        result_artifacts: list[dict[str, Any]] | None = None,
        result_warnings: list[str] | None = None,
        result_error: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.summary = summary
        self.result_metrics = result_metrics
        self.result_execution = result_execution
        self.result_artifacts = list(result_artifacts or [])
        self.result_warnings = list(result_warnings or [])
        self.result_error = result_error


class RunnerConfigValidationError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class RunnerResult:
    status: Literal["succeeded", "failed"] = "succeeded"
    summary: dict[str, Any] | None = None
    failure_message: str | None = None
    result_metrics: dict[str, Any] | None = None
    result_execution: dict[str, Any] | None = None
    result_artifacts: list[dict[str, Any]] = field(default_factory=list)
    result_warnings: list[str] = field(default_factory=list)
    result_error: dict[str, Any] | None = None


class Runner(Protocol):
    runner_type: str

    def normalize_config(self, config: Mapping[str, Any]) -> dict[str, Any]:
        ...

    def execute(self, run: Run, attempt: RunAttempt) -> RunnerResult:
        ...
