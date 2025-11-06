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
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("active_deck_id", sa.Integer(), nullable=True)
        )
        batch_op.create_index("ix_users_active_deck_id", ["active_deck_id"])
        batch_op.create_foreign_key(
            "fk_users_active_deck_id_decks",
            "decks",
            ["active_deck_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    """Remove active_deck_id from users table."""
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_constraint("fk_users_active_deck_id_decks", type_="foreignkey")
        batch_op.drop_index("ix_users_active_deck_id")
        batch_op.drop_column("active_deck_id")
