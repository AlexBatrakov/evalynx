from __future__ import annotations

from app.workers.jobs import process_attempt_job
from app.workers.queue import RQRunQueue
import app.workers.queue as queue_module


def test_rq_run_queue_uses_configured_queue_and_job(monkeypatch) -> None:
    observed: dict[str, object] = {}

    class FakeRedis:
        def close(self) -> None:
            observed["closed"] = True

    class FakeQueue:
        def __init__(self, name: str, *, connection: object, default_timeout: int) -> None:
            observed["queue_name"] = name
            observed["connection"] = connection
            observed["default_timeout"] = default_timeout

        def enqueue(self, func, attempt_id: int, **kwargs) -> None:
            observed["func"] = func
            observed["attempt_id"] = attempt_id
            observed["job_timeout"] = kwargs["job_timeout"]

    def fake_create_redis_connection(redis_url: str) -> FakeRedis:
        observed["redis_url"] = redis_url
        return FakeRedis()

    monkeypatch.setattr(queue_module, "create_redis_connection", fake_create_redis_connection)
    monkeypatch.setattr(queue_module, "Queue", FakeQueue)

    run_queue = RQRunQueue(
        redis_url="redis://queue-test:6379/0",
        queue_name="packet-06",
        job_timeout=42,
    )

    run_queue.enqueue(7)
    run_queue.shutdown()

    assert observed["redis_url"] == "redis://queue-test:6379/0"
    assert observed["queue_name"] == "packet-06"
    assert observed["default_timeout"] == 42
    assert observed["func"] is process_attempt_job
    assert observed["attempt_id"] == 7
    assert observed["job_timeout"] == 42
    assert observed["closed"] is True
