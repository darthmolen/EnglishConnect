"""Add lesson_phases table and phase tracking to user_progress.

Revision ID: 001_add_lesson_phases
Revises:
Create Date: 2025-12-23
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_add_lesson_phases"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create lesson_phases table
    op.create_table(
        "lesson_phases",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("lesson_id", sa.Integer(), nullable=False),
        sa.Column("phase_type", sa.String(50), nullable=False),
        sa.Column("phase_name", sa.String(100), nullable=False),
        sa.Column("sort_order", sa.Integer(), default=0, nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lesson_phases_lesson_id", "lesson_phases", ["lesson_id"])

    # Add phase tracking columns to user_progress
    op.add_column(
        "user_progress",
        sa.Column("phase_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "user_progress",
        sa.Column(
            "phase_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
    )
    op.create_foreign_key(
        "fk_user_progress_phase_id",
        "user_progress",
        "lesson_phases",
        ["phase_id"],
        ["id"],
    )

    # Seed default phases for all existing lessons
    # Standard phases: intro, vocabulary, patterns, practice, wrapup
    op.execute(
        """
        INSERT INTO lesson_phases (lesson_id, phase_type, phase_name, sort_order)
        SELECT id, 'intro', 'Introduction', 0 FROM lessons
        UNION ALL
        SELECT id, 'vocabulary', 'Vocabulary', 1 FROM lessons
        UNION ALL
        SELECT id, 'patterns', 'Q&A Patterns', 2 FROM lessons
        UNION ALL
        SELECT id, 'practice', 'Practice', 3 FROM lessons
        UNION ALL
        SELECT id, 'wrapup', 'Wrap-up', 4 FROM lessons
        """
    )


def downgrade() -> None:
    # Remove foreign key and columns from user_progress
    op.drop_constraint("fk_user_progress_phase_id", "user_progress", type_="foreignkey")
    op.drop_column("user_progress", "phase_state")
    op.drop_column("user_progress", "phase_id")

    # Drop lesson_phases table
    op.drop_index("ix_lesson_phases_lesson_id", table_name="lesson_phases")
    op.drop_table("lesson_phases")
