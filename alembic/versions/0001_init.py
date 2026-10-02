"""init: pgvector extension, repositories, repo_files

Revision ID: 0001
Revises:
Create Date: 2026-09-22
"""
import sqlalchemy as sa

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "repositories",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("owner", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("default_branch", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("html_url", sa.String(500), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_repositories_full_name", "repositories", ["full_name"], unique=True)

    op.create_table(
        "repo_files",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "repository_id",
            sa.Integer,
            sa.ForeignKey("repositories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("path", sa.Text, nullable=False),
        sa.Column("sha", sa.String(40), nullable=False),
        sa.Column("size", sa.Integer, nullable=False),
        sa.Column("language", sa.String(50), nullable=True),
        sa.UniqueConstraint("repository_id", "path", name="uq_repo_file_path"),
    )
    op.create_index("ix_repo_files_repository_id", "repo_files", ["repository_id"])


def downgrade() -> None:
    op.drop_table("repo_files")
    op.drop_table("repositories")
