from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0002_add_run_result_fields"
down_revision = "0001_create_projects_and_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("runs", sa.Column("result_metrics", sa.JSON(), nullable=True))
    op.add_column("runs", sa.Column("result_execution", sa.JSON(), nullable=True))
    op.add_column("runs", sa.Column("result_artifacts", sa.JSON(), nullable=True))
    op.add_column("runs", sa.Column("result_warnings", sa.JSON(), nullable=True))
    op.add_column("runs", sa.Column("result_error", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("runs", "result_error")
    op.drop_column("runs", "result_warnings")
    op.drop_column("runs", "result_artifacts")
    op.drop_column("runs", "result_execution")
    op.drop_column("runs", "result_metrics")
