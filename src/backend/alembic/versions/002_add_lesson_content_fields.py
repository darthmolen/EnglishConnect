"""Add learning_principle_full, ponder_questions, and pattern_images to lessons.

Revision ID: 002_add_lesson_content_fields
Revises: 001_add_lesson_phases
Create Date: 2025-12-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "002_add_lesson_content_fields"
down_revision: Union[str, None] = "001_add_lesson_phases"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new content columns to lessons table
    op.add_column(
        "lessons",
        sa.Column("learning_principle_full", sa.Text(), nullable=True),
    )
    op.add_column(
        "lessons",
        sa.Column(
            "ponder_questions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "lessons",
        sa.Column(
            "pattern_images",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("lessons", "pattern_images")
    op.drop_column("lessons", "ponder_questions")
    op.drop_column("lessons", "learning_principle_full")
