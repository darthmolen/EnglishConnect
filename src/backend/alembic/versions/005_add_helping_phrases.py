"""Add helping phrases table for bilingual practice support.

Revision ID: 005_add_helping_phrases
Revises: 004_add_jwt_auth
Create Date: 2026-01-28

Helping phrases allow students to request assistance during practice
in their native language (e.g., "No entiendo", "Repite, por favor").
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "005_add_helping_phrases"
down_revision: Union[str, None] = "ef47914574a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create helping_phrases table
    op.create_table(
        "helping_phrases",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("language_code", sa.String(10), nullable=False),
        sa.Column("phrase_key", sa.String(50), nullable=False),
        sa.Column("phrase_text", sa.String(200), nullable=False),
        sa.Column("english_meaning", sa.String(200), nullable=False),
        sa.Column("usage_context", sa.Text(), nullable=True),
        sa.Column("display_order", sa.Integer(), default=0),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("language_code", "phrase_key", name="uq_helping_phrase_lang_key"),
    )

    # Create index for language lookups
    op.create_index(
        "ix_helping_phrases_language_code",
        "helping_phrases",
        ["language_code"],
    )

    # Seed Spanish helping phrases
    op.execute(
        """
        INSERT INTO helping_phrases (language_code, phrase_key, phrase_text, english_meaning, usage_context, display_order) VALUES
        ('es', 'repeat', 'Repite, por favor', 'Please repeat', 'When you did not catch what was said', 1),
        ('es', 'dont_understand', 'No entiendo', 'I don''t understand', 'When you need an explanation', 2),
        ('es', 'slower', 'Más despacio, por favor', 'Slower, please', 'When speaking is too fast', 3),
        ('es', 'example', 'Dame un ejemplo', 'Give me an example', 'When you need a concrete example', 4)
        """
    )

    # Seed English helping phrases (for English-speaking learners)
    op.execute(
        """
        INSERT INTO helping_phrases (language_code, phrase_key, phrase_text, english_meaning, usage_context, display_order) VALUES
        ('en', 'repeat', 'Please repeat', 'Please repeat', 'When you did not catch what was said', 1),
        ('en', 'dont_understand', 'I don''t understand', 'I don''t understand', 'When you need an explanation', 2),
        ('en', 'slower', 'Slower, please', 'Slower, please', 'When speaking is too fast', 3),
        ('en', 'example', 'Give me an example', 'Give me an example', 'When you need a concrete example', 4)
        """
    )


def downgrade() -> None:
    op.drop_index("ix_helping_phrases_language_code", table_name="helping_phrases")
    op.drop_table("helping_phrases")
