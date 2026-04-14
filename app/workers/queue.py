from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from collections.abc import Callable
from typing import Protocol

from redis import Redis
from rq import Queue

from app.core.config import Settings
from app.workers.jobs import process_attempt_job


class RunQueue(Protocol):
    def enqueue(self, attempt_id: int) -> None:
        ...


class BackgroundRunQueue:
    def __init__(self, process_attempt: Callable[[int], None], *, max_workers: int = 2) -> None:
        self._process_attempt = process_attempt
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="evalynx-worker",
        )

    def enqueue(self, attempt_id: int) -> None:
        self._executor.submit(self._process_attempt, attempt_id)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=True, cancel_futures=False)


def create_redis_connection(redis_url: str) -> Redis:
    return Redis.from_url(redis_url)


def close_redis_connection(connection: Redis) -> None:
    close = getattr(connection, "close", None)
    if callable(close):
        close()
        return

    connection.connection_pool.disconnect()


class RQRunQueue:
    def __init__(
        self,
        *,
        redis_url: str,
        queue_name: str,
        job_timeout: int,
    ) -> None:
        self._connection = create_redis_connection(redis_url)
        self._queue = Queue(
            queue_name,
            connection=self._connection,
            default_timeout=job_timeout,
        )
        self._job_timeout = job_timeout

    def enqueue(self, attempt_id: int) -> None:
        self._queue.enqueue(
            process_attempt_job,
            attempt_id,
            job_timeout=self._job_timeout,
        )

    def shutdown(self) -> None:
        close_redis_connection(self._connection)


def build_default_run_queue(settings: Settings) -> RunQueue:
    return RQRunQueue(
        redis_url=settings.redis_url,
        queue_name=settings.rq_queue_name,
        job_timeout=settings.rq_job_timeout,
    )
