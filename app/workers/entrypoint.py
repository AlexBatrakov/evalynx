from __future__ import annotations

from rq import Worker

from app.core.config import get_settings
from app.workers.queue import close_redis_connection, create_redis_connection


def main() -> int:
    settings = get_settings()
    connection = create_redis_connection(settings.redis_url)

    try:
        worker = Worker(
            [settings.rq_queue_name],
            connection=connection,
        )
        worker.work(with_scheduler=False)
    finally:
        close_redis_connection(connection)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
