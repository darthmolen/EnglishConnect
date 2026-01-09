"""Add JWT authentication tables and user fields.

Revision ID: 004_add_jwt_auth
Revises: 003_add_spanish_pattern_fields
Create Date: 2025-01-09
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "004_add_jwt_auth"
down_revision: Union[str, None] = "003_add_spanish_pattern_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create roles table
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(50), nullable=False, unique=True),
        sa.Column("description", sa.String(255), nullable=True),
    )

    # Seed default roles
    op.execute(
        """
        INSERT INTO roles (name, description) VALUES
        ('admin', 'Administrator with full access'),
        ('teacher', 'Teacher/instructor role'),
        ('student', 'Student learner role')
        """
    )

    # Create user_roles join table
    op.create_table(
        "user_roles",
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "role_id",
            sa.Integer(),
            sa.ForeignKey("roles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "assigned_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "assigned_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
    )

    # Create refresh_tokens table
    op.create_table(
        "refresh_tokens",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])

    # Create password_reset_tokens table
    op.create_table(
        "password_reset_tokens",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"]
    )

    # Add new columns to users table
    op.add_column("users", sa.Column("password_hash", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("first_name", sa.String(100), nullable=True))
    op.add_column("users", sa.Column("last_name", sa.String(100), nullable=True))
    op.add_column(
        "users",
        sa.Column("is_approved", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column(
        "users",
        sa.Column(
            "approval_status",
            sa.String(20),
            server_default="pending",
            nullable=False,
        ),
    )
    op.add_column("users", sa.Column("approved_at", sa.DateTime(), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "approved_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "auth_provider", sa.String(20), server_default="local", nullable=False
        ),
    )

    # Update existing OAuth users to be approved
    op.execute(
        """
        UPDATE users
        SET auth_provider = 'azure_ad',
            is_approved = true,
            approval_status = 'approved'
        WHERE oauth_provider IS NOT NULL
        """
    )


def downgrade() -> None:
    # Remove columns from users table
    op.drop_column("users", "auth_provider")
    op.drop_column("users", "approved_by")
    op.drop_column("users", "approved_at")
    op.drop_column("users", "approval_status")
    op.drop_column("users", "is_approved")
    op.drop_column("users", "last_name")
    op.drop_column("users", "first_name")
    op.drop_column("users", "password_hash")

    # Drop tables
    op.drop_index("ix_password_reset_tokens_user_id", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_table("user_roles")
    op.drop_table("roles")
