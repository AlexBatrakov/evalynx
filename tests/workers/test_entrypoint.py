from __future__ import annotations

from app.core.config import Settings
from app.workers.entrypoint import main
import app.workers.entrypoint as entrypoint_module


def test_worker_entrypoint_uses_configured_queue(monkeypatch) -> None:
    observed: dict[str, object] = {}

    class FakeConnection:
        pass

    class FakeWorker:
        def __init__(self, queues: list[str], *, connection: object) -> None:
            observed["queues"] = queues
            observed["connection"] = connection

        def work(self, *, with_scheduler: bool) -> None:
            observed["with_scheduler"] = with_scheduler

    monkeypatch.setattr(
        entrypoint_module,
        "get_settings",
        lambda: Settings(
            environment="test",
            database_url="sqlite:///./unused.db",
            redis_url="redis://worker-test:6379/0",
            rq_queue_name="evalynx-runs-ci",
        ),
    )

    def fake_create_redis_connection(redis_url: str) -> FakeConnection:
        observed["redis_url"] = redis_url
        return FakeConnection()

    def fake_close_redis_connection(connection: object) -> None:
        observed["closed_connection"] = connection

    monkeypatch.setattr(entrypoint_module, "create_redis_connection", fake_create_redis_connection)
    monkeypatch.setattr(entrypoint_module, "close_redis_connection", fake_close_redis_connection)
    monkeypatch.setattr(entrypoint_module, "Worker", FakeWorker)

    exit_code = main()

    assert exit_code == 0
    assert observed["redis_url"] == "redis://worker-test:6379/0"
    assert observed["queues"] == ["evalynx-runs-ci"]
    assert observed["with_scheduler"] is False
    assert observed["closed_connection"] is observed["connection"]
