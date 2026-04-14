from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0003_add_run_attempts"
down_revision = "0002_add_run_result_fields"
branch_labels = None
depends_on = None


RUN_STATUS_NAMES = {
    "QUEUED",
    "RUNNING",
    "SUCCEEDED",
    "FAILED",
}


run_status = sa.Enum(
    "QUEUED",
    "RUNNING",
    "SUCCEEDED",
    "FAILED",
    name="run_status",
    native_enum=False,
)

runs_table = sa.table(
    "runs",
    sa.column("id", sa.Integer()),
    sa.column("status", sa.String()),
    sa.column("summary", sa.JSON()),
    sa.column("result_metrics", sa.JSON()),
    sa.column("result_execution", sa.JSON()),
    sa.column("result_artifacts", sa.JSON()),
    sa.column("result_warnings", sa.JSON()),
    sa.column("result_error", sa.JSON()),
    sa.column("failure_message", sa.Text()),
    sa.column("created_at", sa.DateTime(timezone=True)),
    sa.column("started_at", sa.DateTime(timezone=True)),
    sa.column("finished_at", sa.DateTime(timezone=True)),
    sa.column("current_attempt_id", sa.Integer()),
)

run_attempts_table = sa.table(
    "run_attempts",
    sa.column("id", sa.Integer()),
    sa.column("run_id", sa.Integer()),
    sa.column("attempt_number", sa.Integer()),
    sa.column("status", sa.String()),
    sa.column("summary", sa.JSON()),
    sa.column("result_metrics", sa.JSON()),
    sa.column("result_execution", sa.JSON()),
    sa.column("result_artifacts", sa.JSON()),
    sa.column("result_warnings", sa.JSON()),
    sa.column("result_error", sa.JSON()),
    sa.column("failure_message", sa.Text()),
    sa.column("created_at", sa.DateTime(timezone=True)),
    sa.column("started_at", sa.DateTime(timezone=True)),
    sa.column("finished_at", sa.DateTime(timezone=True)),
)


def _normalize_run_status(value: object) -> str:
    if isinstance(value, str):
        normalized = value.strip().upper()
        if normalized in RUN_STATUS_NAMES:
            return normalized

    raise ValueError(f"Unexpected run status value during migration: {value!r}")


def upgrade() -> None:
    op.create_table(
        "run_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", run_status, nullable=False),
        sa.Column("summary", sa.JSON(), nullable=True),
        sa.Column("result_metrics", sa.JSON(), nullable=True),
        sa.Column("result_execution", sa.JSON(), nullable=True),
        sa.Column("result_artifacts", sa.JSON(), nullable=True),
        sa.Column("result_warnings", sa.JSON(), nullable=True),
        sa.Column("result_error", sa.JSON(), nullable=True),
        sa.Column("failure_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("run_id", "attempt_number", name="uq_run_attempts_run_id_attempt_number"),
    )
    op.create_index("ix_run_attempts_run_id", "run_attempts", ["run_id"])

    with op.batch_alter_table("runs") as batch_op:
        batch_op.add_column(sa.Column("current_attempt_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_runs_current_attempt_id", ["current_attempt_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_runs_current_attempt_id_run_attempts",
            "run_attempts",
            ["current_attempt_id"],
            ["id"],
        )

    connection = op.get_bind()
    existing_runs = connection.execute(
        sa.select(
            runs_table.c.id,
            runs_table.c.status,
            runs_table.c.summary,
            runs_table.c.result_metrics,
            runs_table.c.result_execution,
            runs_table.c.result_artifacts,
            runs_table.c.result_warnings,
            runs_table.c.result_error,
            runs_table.c.failure_message,
            runs_table.c.created_at,
            runs_table.c.started_at,
            runs_table.c.finished_at,
        )
    ).mappings()

    for run in existing_runs:
        insert_result = connection.execute(
            run_attempts_table.insert().values(
                run_id=run["id"],
                attempt_number=1,
                status=_normalize_run_status(run["status"]),
                summary=run["summary"],
                result_metrics=run["result_metrics"],
                result_execution=run["result_execution"],
                result_artifacts=run["result_artifacts"],
                result_warnings=run["result_warnings"],
                result_error=run["result_error"],
                failure_message=run["failure_message"],
                created_at=run["created_at"],
                started_at=run["started_at"],
                finished_at=run["finished_at"],
            )
        )
        inserted_primary_key = insert_result.inserted_primary_key
        attempt_id = inserted_primary_key[0] if inserted_primary_key else insert_result.lastrowid
        connection.execute(
            runs_table.update()
            .where(runs_table.c.id == run["id"])
            .values(current_attempt_id=attempt_id)
        )


def downgrade() -> None:
    with op.batch_alter_table("runs") as batch_op:
        batch_op.drop_constraint("fk_runs_current_attempt_id_run_attempts", type_="foreignkey")
        batch_op.drop_index("ix_runs_current_attempt_id")
        batch_op.drop_column("current_attempt_id")

    op.drop_index("ix_run_attempts_run_id", table_name="run_attempts")
    op.drop_table("run_attempts")
