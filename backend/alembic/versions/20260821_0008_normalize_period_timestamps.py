"""Normalize all temporal validity columns to timezone-aware timestamps.

Revision ID: 20260821_0008
Revises: 20260821_0007
"""

from alembic import op
import sqlalchemy as sa


revision = '20260821_0008'
down_revision = '20260821_0007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != 'postgresql':
        return
    schema = op.get_context().config.attributes.get('database_schema')
    for table in ('user_activity_periods', 'area_activity_periods'):
        for column in ('active_from', 'active_until'):
            op.alter_column(
                table,
                column,
                schema=schema,
                existing_type=sa.DateTime(timezone=False),
                type_=sa.DateTime(timezone=True),
                postgresql_using=f'{column} AT TIME ZONE \'UTC\'',
            )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != 'postgresql':
        return
    schema = op.get_context().config.attributes.get('database_schema')
    for table in ('area_activity_periods', 'user_activity_periods'):
        for column in ('active_until', 'active_from'):
            op.alter_column(
                table,
                column,
                schema=schema,
                existing_type=sa.DateTime(timezone=True),
                type_=sa.DateTime(timezone=False),
                postgresql_using=f'{column} AT TIME ZONE \'UTC\'',
            )
