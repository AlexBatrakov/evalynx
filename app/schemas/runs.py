from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import RunStatus


class RunCreate(BaseModel):
    project_id: int
    runner_type: str = "stub"
    config: dict[str, Any] = Field(default_factory=dict)


class RunAttemptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    attempt_number: int
    status: RunStatus
    summary: dict[str, Any] | None
    result_metrics: dict[str, Any] | None
    result_execution: dict[str, Any] | None
    result_artifacts: list[dict[str, Any]] | None
    result_warnings: list[str] | None
    result_error: dict[str, Any] | None
    failure_message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class RunSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    runner_type: str
    status: RunStatus
    current_attempt_number: int | None
    attempt_count: int
    submitted_config: dict[str, Any]
    normalized_config: dict[str, Any]
    config_hash: str
    summary: dict[str, Any] | None
    result_metrics: dict[str, Any] | None
    result_execution: dict[str, Any] | None
    result_artifacts: list[dict[str, Any]] | None
    result_warnings: list[str] | None
    result_error: dict[str, Any] | None
    failure_message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class RunRead(RunSummaryRead):
    attempts: list[RunAttemptRead]
