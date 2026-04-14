from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Run, RunStatus, utcnow
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

    def process_run(self, run_id: int) -> None:
        with self._session_factory() as session:
            run = session.get(Run, run_id)
            if run is None or run.status is not RunStatus.QUEUED:
                return

            runner = self._runner_registry.get(run.runner_type)
            if runner is None:
                self._persist_terminal_result(
                    session,
                    run,
                    RunnerResult(
                        status="failed",
                        failure_message=f"Runner type '{run.runner_type}' is not available in the worker.",
                        result_error={
                            "kind": "worker_runner_missing",
                            "message": f"Runner type '{run.runner_type}' is not available in the worker.",
                        },
                    ),
                )
                return

            run.status = RunStatus.RUNNING
            run.started_at = utcnow()
            session.commit()
            session.refresh(run)

            try:
                result = runner.execute(run)
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

            self._persist_terminal_result(session, run, result)

    def _persist_terminal_result(self, session: Session, run: Run, result: RunnerResult) -> None:
        run.status = RunStatus.SUCCEEDED if result.status == "succeeded" else RunStatus.FAILED
        run.summary = result.summary
        run.result_metrics = result.result_metrics
        run.result_execution = result.result_execution
        run.result_artifacts = list(result.result_artifacts)
        run.result_warnings = list(result.result_warnings)
        run.result_error = result.result_error
        run.failure_message = result.failure_message
        run.finished_at = utcnow()
        session.commit()
