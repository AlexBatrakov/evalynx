from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy import update
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Run, RunAttempt, RunStatus, utcnow
from app.runners.base import Runner, RunnerExecutionError, RunnerResult


class RunWorker:
    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        runner_registry: Mapping[str, Runner],
    ) -> None:
        self._session_factory = session_factory
        self._runner_registry = dict(runner_registry)

    def process_attempt(self, attempt_id: int) -> None:
        with self._session_factory() as session:
            attempt = session.get(RunAttempt, attempt_id)
            if attempt is None:
                return

            if not self._claim_attempt(
                session,
                run_id=attempt.run_id,
                attempt_id=attempt_id,
            ):
                return

            run = session.get(Run, attempt.run_id)
            attempt = session.get(RunAttempt, attempt_id)
            if run is None or attempt is None:
                return

            runner = self._runner_registry.get(run.runner_type)
            if runner is None:
                self._persist_terminal_result(
                    session,
                    run_id=run.id,
                    attempt_id=attempt.id,
                    result=RunnerResult(
                        status="failed",
                        failure_message=f"Runner type '{run.runner_type}' is not available in the worker.",
                        result_error={
                            "kind": "worker_runner_missing",
                            "message": f"Runner type '{run.runner_type}' is not available in the worker.",
                        },
                    ),
                )
                return

            try:
                result = runner.execute(run, attempt)
            except RunnerExecutionError as exc:
                result = RunnerResult(
                    status="failed",
                    summary=exc.summary,
                    failure_message=str(exc),
                    result_metrics=exc.result_metrics,
                    result_execution=exc.result_execution,
                    result_artifacts=exc.result_artifacts,
                    result_warnings=exc.result_warnings,
                    result_error=exc.result_error or {
                        "kind": "runner_execution_error",
                        "message": str(exc),
                    },
                )
            except Exception as exc:  # pragma: no cover - defensive guard
                result = RunnerResult(
                    status="failed",
                    failure_message=f"Unhandled worker error: {exc}",
                    result_error={
                        "kind": "unhandled_worker_error",
                        "message": f"Unhandled worker error: {exc}",
                    },
                )

            self._persist_terminal_result(
                session,
                run_id=run.id,
                attempt_id=attempt.id,
                result=result,
            )

    def _claim_attempt(self, session: Session, *, run_id: int, attempt_id: int) -> bool:
        started_at = utcnow()
        claimed_attempt = session.execute(
            update(RunAttempt)
            .where(
                RunAttempt.id == attempt_id,
                RunAttempt.status == RunStatus.QUEUED,
            )
            .values(
                status=RunStatus.RUNNING,
                started_at=started_at,
            )
        )
        if claimed_attempt.rowcount != 1:
            session.rollback()
            return False

        claimed_run = session.execute(
            update(Run)
            .where(
                Run.id == run_id,
                Run.current_attempt_id == attempt_id,
                Run.status == RunStatus.QUEUED,
            )
            .values(
                status=RunStatus.RUNNING,
                started_at=started_at,
            )
        )
        if claimed_run.rowcount != 1:
            session.rollback()
            return False

        session.commit()

        return True

    def _persist_terminal_result(
        self,
        session: Session,
        *,
        run_id: int,
        attempt_id: int,
        result: RunnerResult,
    ) -> None:
        finished_at = utcnow()
        terminal_status = RunStatus.SUCCEEDED if result.status == "succeeded" else RunStatus.FAILED
        values = {
            "status": terminal_status,
            "summary": result.summary,
            "result_metrics": result.result_metrics,
            "result_execution": result.result_execution,
            "result_artifacts": list(result.result_artifacts),
            "result_warnings": list(result.result_warnings),
            "result_error": result.result_error,
            "failure_message": result.failure_message,
            "finished_at": finished_at,
        }

        updated_attempt = session.execute(
            update(RunAttempt)
            .where(
                RunAttempt.id == attempt_id,
                RunAttempt.status == RunStatus.RUNNING,
            )
            .values(**values)
        )
        if updated_attempt.rowcount != 1:
            session.rollback()
            return

        session.execute(
            update(Run)
            .where(
                Run.id == run_id,
                Run.current_attempt_id == attempt_id,
            )
            .values(**values)
        )
        session.commit()
