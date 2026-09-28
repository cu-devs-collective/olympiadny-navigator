"""Add personal routes and a durable notification outbox."""

import sqlalchemy as sa
from alembic import op


revision = "20260930_0002"
down_revision = "20260922_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "students",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("max_user_id", sa.BigInteger(), unique=True),
        sa.Column("profile", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
    )
    op.create_table(
        "login_sessions",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(80), sa.ForeignKey("students.id"), nullable=False),
        sa.Column("expires_at", sa.Float(), nullable=False),
    )
    op.create_index("ix_login_sessions_user_id", "login_sessions", ["user_id"])
    op.create_table(
        "track_items",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("user_id", sa.String(80), sa.ForeignKey("students.id"), nullable=False),
        sa.Column("olympiad_id", sa.String(80), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.UniqueConstraint("user_id", "olympiad_id"),
    )
    op.create_index("ix_track_items_user_id", "track_items", ["user_id"])
    op.create_table(
        "reminders",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("user_id", sa.String(80), sa.ForeignKey("students.id"), nullable=False),
        sa.Column("olympiad_id", sa.String(80), nullable=False),
        sa.Column("dedup_key", sa.String(180), nullable=False),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("due_at", sa.Float(), nullable=False),
        sa.Column("deadline", sa.Float(), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("is_demo", sa.Boolean(), nullable=False),
        sa.Column("sent_at", sa.Float()),
        sa.Column("claimed_at", sa.Float()),
        sa.Column("error", sa.String(300)),
        sa.UniqueConstraint("user_id", "dedup_key"),
    )
    for column in ("user_id", "due_at", "state"):
        op.create_index(f"ix_reminders_{column}", "reminders", [column])


def downgrade() -> None:
    for table in ("reminders", "track_items", "login_sessions", "students"):
        op.drop_table(table)
