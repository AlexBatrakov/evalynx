from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Run, RunStatus


class RunRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

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

    def get(self, run_id: int) -> Run | None:
        return self._session.get(Run, run_id)

    def list(self) -> list[Run]:
        statement = select(Run).order_by(Run.id.desc())
        return list(self._session.scalars(statement))

    def list_by_project(self, project_id: int) -> list[Run]:
        statement = (
            select(Run)
            .where(Run.project_id == project_id)
            .order_by(Run.id.desc())
        )
        return list(self._session.scalars(statement))
