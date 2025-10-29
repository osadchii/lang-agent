"""Initial schema for Telegram users and message history."""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create users and messages tables."""
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        pg_enum = postgresql.ENUM(
            "inbound",
            "outbound",
            name="messagedirection",
            create_type=True,
        )
        pg_enum.create(bind, checkfirst=True)
        direction_column_type = postgresql.ENUM(
            "inbound",
            "outbound",
            name="messagedirection",
            create_type=False,
        )
    else:
        direction_column_type = sa.Enum(
            "inbound",
            "outbound",
            name="messagedirection",
        )

    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("first_name", sa.String(length=255), nullable=True),
        sa.Column("last_name", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("direction", direction_column_type, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_messages_user_id", "messages", ["user_id"])
    op.create_index("ix_messages_created_at", "messages", ["created_at"])


def downgrade() -> None:
    """Drop messages and users tables."""
    bind = op.get_bind()
    op.drop_index("ix_messages_created_at", table_name="messages")
    op.drop_index("ix_messages_user_id", table_name="messages")
    op.drop_table("messages")
    op.drop_table("users")
    if bind.dialect.name == "postgresql":
        pg_enum = postgresql.ENUM(
            "inbound",
            "outbound",
            name="messagedirection",
            create_type=False,
        )
        pg_enum.drop(bind, checkfirst=True)
