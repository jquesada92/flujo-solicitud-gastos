"""Add revocable, one-time password reset link versioning.

Revision ID: 20260824_0010
Revises: 20260824_0009
"""

from alembic import op
import sqlalchemy as sa


revision = '20260824_0010'
down_revision = '20260824_0009'
branch_labels = None
depends_on = None


def _schema() -> str | None:
    return op.get_context().config.attributes.get('database_schema')


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column(
            'password_reset_version',
            sa.Integer(),
            nullable=False,
            server_default=sa.text('0'),
        ),
        schema=_schema(),
    )


def downgrade() -> None:
    op.drop_column('users', 'password_reset_version', schema=_schema())
