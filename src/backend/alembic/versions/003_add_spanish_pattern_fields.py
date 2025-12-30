"""Add Spanish translation fields to qa_patterns table.

Revision ID: 003_add_spanish_pattern_fields
Revises: 002_add_lesson_content_fields
Create Date: 2025-12-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "003_add_spanish_pattern_fields"
down_revision: Union[str, None] = "002_add_lesson_content_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add Spanish translation columns to qa_patterns table
    op.add_column(
        "qa_patterns",
        sa.Column("question_template_es", sa.String(500), nullable=True),
    )
    op.add_column(
        "qa_patterns",
        sa.Column("answer_template_es", sa.String(500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("qa_patterns", "answer_template_es")
    op.drop_column("qa_patterns", "question_template_es")
