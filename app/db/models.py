from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )

    runs: Mapped[list["Run"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    runner_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, name="run_status", native_enum=False),
        nullable=False,
        default=RunStatus.QUEUED,
    )
    submitted_config: Mapped[dict[str, Any]] = mapped_column(JSON(), nullable=False)
    normalized_config: Mapped[dict[str, Any]] = mapped_column(JSON(), nullable=False)
    config_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    summary: Mapped[dict[str, Any] | None] = mapped_column(JSON(), nullable=True)
    result_metrics: Mapped[dict[str, Any] | None] = mapped_column(JSON(), nullable=True)
    result_execution: Mapped[dict[str, Any] | None] = mapped_column(JSON(), nullable=True)
    result_artifacts: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON(), nullable=True)
    result_warnings: Mapped[list[str] | None] = mapped_column(JSON(), nullable=True)
    result_error: Mapped[dict[str, Any] | None] = mapped_column(JSON(), nullable=True)
    failure_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped[Project] = relationship(back_populates="runs")
