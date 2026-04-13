from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from app.db.models import Run


class RunnerExecutionError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class RunnerResult:
    summary: dict[str, Any]


class Runner(Protocol):
    runner_type: str

    def execute(self, run: Run) -> RunnerResult:
        ...
