"""integrations: GitHub App installations with encrypted credentials

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-02
"""
import sqlalchemy as sa

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "integrations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "organization_id",
            sa.Integer,
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("installation_id", sa.Integer, nullable=False),
        sa.Column("encrypted_creds", sa.Text, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("organization_id", "type", name="uq_org_integration_type"),
    )
    op.create_index("ix_integrations_organization_id", "integrations", ["organization_id"])
    op.create_index("ix_integrations_type", "integrations", ["type"])


def downgrade() -> None:
    op.drop_index("ix_integrations_type")
    op.drop_index("ix_integrations_organization_id")
    op.drop_table("integrations")
