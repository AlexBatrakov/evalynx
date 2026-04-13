"""Runner package placeholder for future packets."""
from app.runners.base import Runner, RunnerExecutionError, RunnerResult
from app.runners.stub import StubRunner


def build_runner_registry() -> dict[str, Runner]:
    stub_runner = StubRunner()
    return {stub_runner.runner_type: stub_runner}


__all__ = [
    "Runner",
    "RunnerExecutionError",
    "RunnerResult",
    "StubRunner",
    "build_runner_registry",
]
