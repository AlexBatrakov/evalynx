from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from collections.abc import Callable
from typing import Protocol


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
