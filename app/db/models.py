from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
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
    current_attempt_id: Mapped[int | None] = mapped_column(
        ForeignKey("run_attempts.id"),
        nullable=True,
        index=True,
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
    attempts: Mapped[list["RunAttempt"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        foreign_keys="RunAttempt.run_id",
        order_by="RunAttempt.attempt_number.asc()",
    )
    current_attempt: Mapped["RunAttempt | None"] = relationship(
        foreign_keys=[current_attempt_id],
        post_update=True,
    )

    @property
    def attempt_count(self) -> int:
        return len(self.attempts)

    @property
    def current_attempt_number(self) -> int | None:
        current_attempt = self.current_attempt
        if current_attempt is None:
            return None

        return current_attempt.attempt_number


class RunAttempt(Base):
    __tablename__ = "run_attempts"
    __table_args__ = (
        UniqueConstraint("run_id", "attempt_number", name="uq_run_attempts_run_id_attempt_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), nullable=False, index=True)
    attempt_number: Mapped[int] = mapped_column(Integer(), nullable=False)
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, name="run_status", native_enum=False),
        nullable=False,
        default=RunStatus.QUEUED,
    )
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

    run: Mapped[Run] = relationship(
        back_populates="attempts",
        foreign_keys=[run_id],
    )
