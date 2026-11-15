"""privacy lifecycle and account deletion requests

Revision ID: phase25_privacy
Revises: f717fd814eac
"""
from alembic import op
import sqlalchemy as sa

revision = "phase25_privacy"
down_revision = "f717fd814eac"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "account_deletion_requests",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("reason", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.String(length=36), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outcome_summary", sa.Text(), nullable=False, server_default=""),
    )
    op.create_index("ix_account_deletion_requests_user_id", "account_deletion_requests", ["user_id"])
    op.create_index("ix_account_deletion_requests_status", "account_deletion_requests", ["status"])


def downgrade():
    op.drop_index("ix_account_deletion_requests_status", table_name="account_deletion_requests")
    op.drop_index("ix_account_deletion_requests_user_id", table_name="account_deletion_requests")
    op.drop_table("account_deletion_requests")
