from __future__ import annotations

from collections.abc import Callable


class ManualRunQueue:
    def __init__(self, process_run: Callable[[int], None]) -> None:
        self._process_run = process_run
        self.pending_run_ids: list[int] = []

    def enqueue(self, run_id: int) -> None:
        self.pending_run_ids.append(run_id)

    def run_next(self) -> int | None:
        if not self.pending_run_ids:
            return None

        run_id = self.pending_run_ids.pop(0)
        self._process_run(run_id)
        return run_id

    def run_all(self) -> list[int]:
        processed: list[int] = []

        while self.pending_run_ids:
            run_id = self.run_next()
            if run_id is not None:
                processed.append(run_id)

        return processed

    def shutdown(self) -> None:
        return None
