from app.core.config import Settings
from app.runners.base import (
    Runner,
    RunnerConfigValidationError,
    RunnerExecutionError,
    RunnerResult,
)
from app.runners.solo_wargame import SoloWargameRunner
from app.runners.stub import StubRunner


def build_runner_registry(settings: Settings) -> dict[str, Runner]:
    stub_runner = StubRunner()
    solo_wargame_runner = SoloWargameRunner(
        repo_path=settings.solo_wargame_repo_path,
        python_command=settings.solo_wargame_python_command,
        artifact_root=settings.artifact_root,
    )
    return {
        solo_wargame_runner.runner_type: solo_wargame_runner,
        stub_runner.runner_type: stub_runner,
    }


__all__ = [
    "Runner",
    "RunnerConfigValidationError",
    "RunnerExecutionError",
    "RunnerResult",
    "SoloWargameRunner",
    "StubRunner",
    "build_runner_registry",
]
