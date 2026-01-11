"""Add criterion_es to evaluation_criteria

Revision ID: ef47914574a5
Revises: 004_add_jwt_auth
Create Date: 2026-01-10 20:55:19.980424

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'ef47914574a5'
down_revision: Union[str, Sequence[str], None] = '004_add_jwt_auth'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('evaluation_criteria', sa.Column('criterion_es', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('evaluation_criteria', 'criterion_es')
