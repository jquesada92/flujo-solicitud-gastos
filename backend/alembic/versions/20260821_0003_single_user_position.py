"""Enforce one organizational Cargo per user.

Revision ID: 20260821_0003
Revises: 20260820_0002
Create Date: 2026-08-21

Cargo remains organizational metadata only and does not grant authorization.
"""

from alembic import context, op
import sqlalchemy as sa


revision = '20260821_0003'
down_revision = '20260820_0002'
branch_labels = None
depends_on = None


def _configured_schema(bind) -> str | None:
    if bind.dialect.name == 'sqlite':
        return None
    schema = context.config.attributes.get('database_schema')
    if not schema:
        raise RuntimeError('DATABASE_SCHEMA must be configured for PostgreSQL migrations')
    return schema


def _qualified(schema: str | None, table: str) -> str:
    return f'"{schema}"."{table}"' if schema else f'"{table}"'


def upgrade() -> None:
    bind = op.get_bind()
    schema = _configured_schema(bind)
    user_positions = _qualified(schema, 'user_positions')

    # Normalize any test/legacy rows before enforcing single-valued Cargo.
    # The oldest assignment is retained deterministically.
    op.execute(sa.text(
        f'DELETE FROM {user_positions} '
        f'WHERE id NOT IN (SELECT MIN(id) FROM {user_positions} GROUP BY user_id)'
    ))

    with op.batch_alter_table('user_positions', schema=schema) as batch:
        batch.drop_constraint('uq_user_position', type_='unique')
        batch.create_unique_constraint('uq_user_position_user', ['user_id'])


def downgrade() -> None:
    bind = op.get_bind()
    schema = _configured_schema(bind)

    with op.batch_alter_table('user_positions', schema=schema) as batch:
        batch.drop_constraint('uq_user_position_user', type_='unique')
        batch.create_unique_constraint('uq_user_position', ['user_id', 'position_id'])
