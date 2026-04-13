from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import RunStatus


class RunCreate(BaseModel):
    project_id: int
    runner_type: str = "stub"
    config: dict[str, Any] = Field(default_factory=dict)


class RunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    runner_type: str
    status: RunStatus
    submitted_config: dict[str, Any]
    normalized_config: dict[str, Any]
    config_hash: str
    summary: dict[str, Any] | None
    failure_message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
