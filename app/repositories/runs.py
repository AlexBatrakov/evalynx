from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Run, RunAttempt, RunStatus


class RunRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _with_attempts(self, statement):
        return statement.options(
            selectinload(Run.current_attempt),
            selectinload(Run.attempts),
        )

    def create(
        self,
        *,
        project_id: int,
        runner_type: str,
        submitted_config: dict[str, Any],
        normalized_config: dict[str, Any],
        config_hash: str,
    ) -> Run:
        run = Run(
            project_id=project_id,
            runner_type=runner_type,
            status=RunStatus.QUEUED,
            submitted_config=submitted_config,
            normalized_config=normalized_config,
            config_hash=config_hash,
        )
        self._session.add(run)
        self._session.flush()
        return run

    def create_attempt(
        self,
        *,
        run: Run,
        attempt_number: int,
    ) -> RunAttempt:
        attempt = RunAttempt(
            run=run,
            attempt_number=attempt_number,
            status=RunStatus.QUEUED,
        )
        self._session.add(attempt)
        self._session.flush()
        return attempt

    def get(self, run_id: int) -> Run | None:
        statement = self._with_attempts(
            select(Run).where(Run.id == run_id)
        )
        return self._session.scalar(statement)

    def get_attempt(self, attempt_id: int) -> RunAttempt | None:
        statement = (
            select(RunAttempt)
            .where(RunAttempt.id == attempt_id)
            .options(selectinload(RunAttempt.run))
        )
        return self._session.scalar(statement)

    def list(self) -> list[Run]:
        statement = self._with_attempts(
            select(Run).order_by(Run.id.desc())
        )
        return list(self._session.scalars(statement))

    def list_by_project(self, project_id: int) -> list[Run]:
        statement = self._with_attempts(
            select(Run)
            .where(Run.project_id == project_id)
            .order_by(Run.id.desc())
        )
        return list(self._session.scalars(statement))
