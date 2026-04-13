from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_create_projects_and_runs"
down_revision = None
branch_labels = None
depends_on = None


run_status = sa.Enum(
    "queued",
    "running",
    "succeeded",
    "failed",
    name="run_status",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("runner_type", sa.String(length=100), nullable=False),
        sa.Column("status", run_status, nullable=False),
        sa.Column("submitted_config", sa.JSON(), nullable=False),
        sa.Column("normalized_config", sa.JSON(), nullable=False),
        sa.Column("config_hash", sa.String(length=64), nullable=False),
        sa.Column("summary", sa.JSON(), nullable=True),
        sa.Column("failure_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_runs_project_id", "runs", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_runs_project_id", table_name="runs")
    op.drop_table("runs")
    op.drop_table("projects")
