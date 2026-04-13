from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import Run
from app.repositories.projects import ProjectRepository
from app.repositories.runs import RunRepository
from app.schemas.runs import RunCreate
from app.services.errors import ProjectNotFoundError, RunNotFoundError, UnsupportedRunnerError
from app.workers.queue import RunQueue


def _normalize_config(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _normalize_config(value[key])
            for key in sorted(value)
        }

    if isinstance(value, list):
        return [_normalize_config(item) for item in value]

    return value


def _compute_config_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class RunService:
    def __init__(
        self,
        *,
        session: Session,
        run_queue: RunQueue,
        supported_runners: set[str],
    ) -> None:
        self._session = session
        self._projects = ProjectRepository(session)
        self._runs = RunRepository(session)
        self._run_queue = run_queue
        self._supported_runners = supported_runners

    def create_run(self, payload: RunCreate) -> Run:
        project = self._projects.get(payload.project_id)
        if project is None:
            raise ProjectNotFoundError(f"Project {payload.project_id} was not found.")

        if payload.runner_type not in self._supported_runners:
            supported = ", ".join(sorted(self._supported_runners))
            raise UnsupportedRunnerError(
                f"Runner type '{payload.runner_type}' is not supported. Supported runners: {supported}."
            )

        normalized_config = _normalize_config(payload.config)
        config_hash = _compute_config_hash(normalized_config)

        run = self._runs.create(
            project_id=project.id,
            runner_type=payload.runner_type,
            submitted_config=payload.config,
            normalized_config=normalized_config,
            config_hash=config_hash,
        )
        self._session.commit()
        self._session.refresh(run)

        try:
            self._run_queue.enqueue(run.id)
        except Exception:
            raise

        return run

    def list_runs(self) -> list[Run]:
        return self._runs.list()

    def get_run(self, run_id: int) -> Run:
        run = self._runs.get(run_id)
        if run is None:
            raise RunNotFoundError(f"Run {run_id} was not found.")

        return run

    def list_project_runs(self, project_id: int) -> list[Run]:
        project = self._projects.get(project_id)
        if project is None:
            raise ProjectNotFoundError(f"Project {project_id} was not found.")

        return self._runs.list_by_project(project_id)
