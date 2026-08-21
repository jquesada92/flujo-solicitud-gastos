"""Add temporal activity periods for users, areas, roles and groups.

Revision ID: 20260821_0005
Revises: 20260821_0004
"""

from alembic import op
import sqlalchemy as sa


revision = '20260821_0005'
down_revision = '20260821_0004'
branch_labels = None
depends_on = None


def _schema() -> str | None:
    return op.get_context().config.attributes.get('database_schema')


def _fk(table: str, column: str):
    schema = _schema()
    target = f'{schema}.{table}.{column}' if schema else f'{table}.{column}'
    return sa.ForeignKey(target, ondelete='CASCADE')


def _create_period_table(name: str, parent_table: str, parent_column: str, *, timezone: bool) -> None:
    entity = name.removesuffix('_activity_periods')
    foreign_key = f'{entity}_id'
    schema = _schema()
    op.create_table(
        name,
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column(foreign_key, sa.Integer(), _fk(parent_table, parent_column), nullable=False),
        sa.Column('active_from', sa.DateTime(timezone=timezone), nullable=False),
        sa.Column('active_until', sa.DateTime(timezone=timezone), nullable=True),
        sa.CheckConstraint(
            'active_until IS NULL OR active_until >= active_from',
            name=f'ck_{entity}_activity_period_dates',
        ),
        schema=schema,
    )
    op.create_index(f'ix_{name}_{foreign_key}', name, [foreign_key], schema=schema)
    op.create_index(
        f'uq_{entity}_activity_period_open',
        name,
        [foreign_key],
        unique=True,
        schema=schema,
        postgresql_where=sa.text('active_until IS NULL'),
        sqlite_where=sa.text('active_until IS NULL'),
    )


def _backfill(period_table: str, parent_table: str, foreign_key: str) -> None:
    schema = _schema()
    prefix = f'{schema}.' if schema else ''
    op.execute(sa.text(
        f'INSERT INTO {prefix}{period_table} ({foreign_key}, active_from, active_until) '
        f'SELECT id, created_at, CASE WHEN active THEN NULL ELSE created_at END '
        f'FROM {prefix}{parent_table}'
    ))


def upgrade() -> None:
    _create_period_table('user_activity_periods', 'users', 'id', timezone=False)
    _create_period_table('area_activity_periods', 'expense_categories', 'id', timezone=False)
    _create_period_table('role_activity_periods', 'roles', 'id', timezone=True)
    _create_period_table('group_activity_periods', 'user_groups', 'id', timezone=True)

    _backfill('user_activity_periods', 'users', 'user_id')
    _backfill('area_activity_periods', 'expense_categories', 'area_id')
    _backfill('role_activity_periods', 'roles', 'role_id')
    _backfill('group_activity_periods', 'user_groups', 'group_id')


def downgrade() -> None:
    schema = _schema()
    for name in (
        'group_activity_periods',
        'role_activity_periods',
        'area_activity_periods',
        'user_activity_periods',
    ):
        op.drop_table(name, schema=schema)

