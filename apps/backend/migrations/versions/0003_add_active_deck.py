"""Add active_deck_id to users table."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_add_active_deck"
down_revision = "0002_flashcards"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add active_deck_id column to users table."""
    op.add_column(
        "users",
        sa.Column("active_deck_id", sa.Integer(), nullable=True),
    )
    op.create_index("ix_users_active_deck_id", "users", ["active_deck_id"])
    op.create_foreign_key(
        "fk_users_active_deck_id_decks",
        "users",
        "decks",
        ["active_deck_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Remove active_deck_id from users table."""
    op.drop_constraint("fk_users_active_deck_id_decks", "users", type_="foreignkey")
    op.drop_index("ix_users_active_deck_id", table_name="users")
    op.drop_column("users", "active_deck_id")
