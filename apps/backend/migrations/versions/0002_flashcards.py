"""Add flashcard decks and scheduling tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_flashcards"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create decks, cards, and user_cards tables."""
    op.create_table(
        "decks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("owner_id", sa.BigInteger(), nullable=True),
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("owner_id", "slug", name="uq_decks_owner_slug"),
    )
    op.create_index("ix_decks_owner_id", "decks", ["owner_id"])

    op.create_table(
        "cards",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("source_language", sa.String(length=16), nullable=False),
        sa.Column("normalized_source_text", sa.String(length=512), nullable=False),
        sa.Column("target_text", sa.Text(), nullable=False),
        sa.Column("target_language", sa.String(length=16), nullable=False),
        sa.Column("normalized_target_text", sa.String(length=512), nullable=False),
        sa.Column("example_sentence", sa.Text(), nullable=False),
        sa.Column("example_translation", sa.Text(), nullable=False),
        sa.Column("part_of_speech", sa.String(length=64), nullable=True),
        sa.Column("extra", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_cards_normalized_source_text",
        "cards",
        ["normalized_source_text"],
        unique=True,
    )
    op.create_index(
        "ix_cards_normalized_target_text",
        "cards",
        ["normalized_target_text"],
    )

    op.create_table(
        "user_cards",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("deck_id", sa.Integer(), nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("last_rating", sa.String(length=32), nullable=True),
        sa.Column("interval_minutes", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("review_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "next_review_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["deck_id"], ["decks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["card_id"], ["cards.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "deck_id", "card_id", name="uq_user_deck_card"),
    )
    op.create_index("ix_user_cards_user_id", "user_cards", ["user_id"])
    op.create_index("ix_user_cards_deck_id", "user_cards", ["deck_id"])
    op.create_index("ix_user_cards_card_id", "user_cards", ["card_id"])
    op.create_index("ix_user_cards_next_review_at", "user_cards", ["next_review_at"])


def downgrade() -> None:
    """Drop flashcard-related tables."""
    op.drop_index("ix_user_cards_next_review_at", table_name="user_cards")
    op.drop_index("ix_user_cards_card_id", table_name="user_cards")
    op.drop_index("ix_user_cards_deck_id", table_name="user_cards")
    op.drop_index("ix_user_cards_user_id", table_name="user_cards")
    op.drop_table("user_cards")

    op.drop_index("ix_cards_normalized_target_text", table_name="cards")
    op.drop_index("ix_cards_normalized_source_text", table_name="cards")
    op.drop_table("cards")

    op.drop_index("ix_decks_owner_id", table_name="decks")
    op.drop_table("decks")
