from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Run, RunStatus, utcnow
from app.runners.base import Runner, RunnerExecutionError


class RunWorker:
    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        runner_registry: Mapping[str, Runner],
    ) -> None:
        self._session_factory = session_factory
        self._runner_registry = dict(runner_registry)

    def process_run(self, run_id: int) -> None:
        with self._session_factory() as session:
            run = session.get(Run, run_id)
            if run is None or run.status is not RunStatus.QUEUED:
                return

            runner = self._runner_registry.get(run.runner_type)
            if runner is None:
                self._mark_failed(
                    session,
                    run,
                    f"Runner type '{run.runner_type}' is not available in the worker.",
                )
                return

            run.status = RunStatus.RUNNING
            run.started_at = utcnow()
            session.commit()
            session.refresh(run)

            try:
                result = runner.execute(run)
            except RunnerExecutionError as exc:
                self._mark_failed(session, run, str(exc))
                return
            except Exception as exc:  # pragma: no cover - defensive guard
                self._mark_failed(session, run, f"Unhandled worker error: {exc}")
                return

            run.status = RunStatus.SUCCEEDED
            run.summary = result.summary
            run.failure_message = None
            run.finished_at = utcnow()
            session.commit()

    def _mark_failed(self, session: Session, run: Run, message: str) -> None:
        run.status = RunStatus.FAILED
        run.failure_message = message
        run.summary = None
        run.finished_at = utcnow()
        session.commit()
