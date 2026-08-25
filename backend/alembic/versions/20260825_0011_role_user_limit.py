"""Add an optional active-user limit to roles.

Revision ID: 20260825_0011
Revises: 20260824_0010
"""

from alembic import op
import sqlalchemy as sa


revision = '20260825_0011'
down_revision = '20260824_0010'
branch_labels = None
depends_on = None


def _schema() -> str | None:
    return op.get_context().config.attributes.get('database_schema')


def _role_periods(bind) -> sa.Table:
    return sa.Table(
        'role_activity_periods',
        sa.MetaData(),
        autoload_with=bind,
        schema=_schema(),
    )


def upgrade() -> None:
    with op.batch_alter_table('roles', schema=_schema()) as batch:
        batch.add_column(sa.Column('max_users', sa.Integer(), nullable=True))
        batch.create_check_constraint(
            'ck_roles_max_users_positive',
            'max_users IS NULL OR max_users >= 1',
        )

    bind = op.get_bind()
    periods = _role_periods(bind)
    rows = bind.execute(sa.select(periods.c.id, periods.c['values'])).mappings().all()
    for row in rows:
        values = dict(row['values'] or {})
        values['max_users'] = None
        bind.execute(
            periods.update().where(periods.c.id == row['id']).values(values=values)
        )


def downgrade() -> None:
    bind = op.get_bind()
    periods = _role_periods(bind)
    rows = bind.execute(sa.select(periods.c.id, periods.c['values'])).mappings().all()
    for row in rows:
        values = dict(row['values'] or {})
        values.pop('max_users', None)
        bind.execute(
            periods.update().where(periods.c.id == row['id']).values(values=values)
        )

    with op.batch_alter_table('roles', schema=_schema()) as batch:
        batch.drop_constraint('ck_roles_max_users_positive', type_='check')
        batch.drop_column('max_users')
