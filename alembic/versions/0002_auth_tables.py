"""auth: users, organizations, org_memberships; add org_id to repositories

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-02
"""
import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("github_id", sa.Integer, nullable=False, unique=True),
        sa.Column("github_login", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_users_github_id", "users", ["github_id"])
    op.create_index("ix_users_github_login", "users", ["github_login"])

    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("github_id", sa.Integer, nullable=False, unique=True),
        sa.Column("slug", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_organizations_github_id", "organizations", ["github_id"])
    op.create_index("ix_organizations_slug", "organizations", ["slug"])

    op.create_table(
        "org_memberships",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            sa.Integer,
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False, default="member"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("user_id", "organization_id", name="uq_user_org"),
    )
    op.create_index("ix_org_memberships_user_id", "org_memberships", ["user_id"])
    op.create_index("ix_org_memberships_organization_id", "org_memberships", ["organization_id"])

    op.add_column("repositories", sa.Column("organization_id", sa.Integer, nullable=True))
    op.create_foreign_key(
        "fk_repositories_organization_id",
        "repositories",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_repositories_organization_id", "repositories", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_repositories_organization_id")
    op.drop_constraint("fk_repositories_organization_id", "repositories", type_="foreignkey")
    op.drop_column("repositories", "organization_id")

    op.drop_table("org_memberships")
    op.drop_index("ix_organizations_slug")
    op.drop_index("ix_organizations_github_id")
    op.drop_table("organizations")

    op.drop_index("ix_users_github_login")
    op.drop_index("ix_users_github_id")
    op.drop_table("users")
