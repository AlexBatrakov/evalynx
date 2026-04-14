from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from alembic import command
from alembic.config import Config


def _alembic_config(database_url: str) -> Config:
    repository_root = Path(__file__).resolve().parents[2]
    config = Config(str(repository_root / "alembic.ini"))
    config.set_main_option("script_location", str(repository_root / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_upgrade_from_packet_04_db_backfills_run_attempts(tmp_path: Path) -> None:
    database_path = tmp_path / "packet04.db"
    database_url = f"sqlite:///{database_path}"
    alembic_config = _alembic_config(database_url)

    command.upgrade(alembic_config, "0002_add_run_result_fields")

    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            insert into projects (id, name, description, created_at)
            values (?, ?, ?, ?)
            """,
            (1, "Migration Project", None, now),
        )
        connection.execute(
            """
            insert into runs (
                id,
                project_id,
                runner_type,
                status,
                submitted_config,
                normalized_config,
                config_hash,
                summary,
                result_metrics,
                result_execution,
                result_artifacts,
                result_warnings,
                result_error,
                failure_message,
                created_at,
                started_at,
                finished_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1,
                1,
                "stub",
                "SUCCEEDED",
                "{}",
                "{}",
                "hash",
                '{"message":"done"}',
                '{"episode_count":1}',
                '{"runner":"stub"}',
                "[]",
                "[]",
                None,
                None,
                now,
                now,
                now,
            ),
        )
        connection.commit()

    command.upgrade(alembic_config, "head")

    with sqlite3.connect(database_path) as connection:
        attempts = connection.execute(
            """
            select run_id, attempt_number, status, summary
            from run_attempts
            order by id
            """
        ).fetchall()
        current_attempt_id = connection.execute(
            "select current_attempt_id from runs where id = 1"
        ).fetchone()[0]

    assert len(attempts) == 1
    assert attempts[0][0:3] == (1, 1, "SUCCEEDED")
    assert json.loads(attempts[0][3]) == {"message": "done"}
    assert current_attempt_id is not None
