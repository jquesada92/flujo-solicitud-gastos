"""Add JSON snapshots to temporal entity periods.

Revision ID: 20260821_0006
Revises: 20260821_0005
"""

from alembic import op
import sqlalchemy as sa


revision = '20260821_0006'
down_revision = '20260821_0005'
branch_labels = None
depends_on = None


def _schema() -> str | None:
    return op.get_context().config.attributes.get('database_schema')


def _table(name: str, metadata: sa.MetaData) -> sa.Table:
    return sa.Table(name, metadata, schema=_schema(), autoload_with=op.get_bind())


def upgrade() -> None:
    period_names = (
        'user_activity_periods', 'area_activity_periods',
        'role_activity_periods', 'group_activity_periods',
    )
    for name in period_names:
        op.add_column(name, sa.Column('values', sa.JSON(), nullable=True), schema=_schema())

    metadata = sa.MetaData()
    users, areas = _table('users', metadata), _table('expense_categories', metadata)
    roles, groups = _table('roles', metadata), _table('user_groups', metadata)
    assignments, group_roles = _table('user_role_assignments', metadata), _table('group_roles', metadata)
    user_periods, area_periods = _table('user_activity_periods', metadata), _table('area_activity_periods', metadata)
    role_periods, group_periods = _table('role_activity_periods', metadata), _table('group_activity_periods', metadata)
    bind = op.get_bind()

    for row in bind.execute(sa.select(users)).mappings():
        assigned = bind.execute(
            sa.select(roles.c.id, roles.c.code, roles.c.name)
            .join(assignments, assignments.c.role_id == roles.c.id)
            .where(assignments.c.user_id == row['id']).order_by(roles.c.code)
        ).mappings().all()
        role_value = row['role'].value if hasattr(row['role'], 'value') else str(row['role'])
        values = {
            'identity_document': row['identity_document'], 'phone': row['phone'],
            'first_name': row['first_name'], 'middle_name': row['middle_name'],
            'last_name': row['last_name'], 'second_last_name': row['second_last_name'],
            'name': row['name'], 'email': row['email'], 'role': role_value,
            'assigned_roles': [dict(item) for item in assigned], 'active': row['active'],
            '_backfilled': True,
        }
        bind.execute(user_periods.update().where(user_periods.c.user_id == row['id']).values(values=values))

    for row in bind.execute(sa.select(areas)).mappings():
        values = {'code': row['code'], 'name': row['name'], 'active': row['active'], '_backfilled': True}
        bind.execute(area_periods.update().where(area_periods.c.area_id == row['id']).values(values=values))

    for row in bind.execute(sa.select(roles)).mappings():
        group = bind.execute(
            sa.select(groups.c.id, groups.c.code, groups.c.name)
            .join(group_roles, group_roles.c.group_id == groups.c.id)
            .where(group_roles.c.role_id == row['id'])
        ).mappings().first()
        values = {
            'code': row['code'], 'name': row['name'], 'description': row['description'],
            'system_managed': row['system_managed'], 'group': dict(group) if group else None,
            'active': row['active'], '_backfilled': True,
        }
        bind.execute(role_periods.update().where(role_periods.c.role_id == row['id']).values(values=values))

    for row in bind.execute(sa.select(groups)).mappings():
        values = {
            'code': row['code'], 'name': row['name'], 'description': row['description'],
            'active': row['active'], '_backfilled': True,
        }
        bind.execute(group_periods.update().where(group_periods.c.group_id == row['id']).values(values=values))

    # Revision 0005 represented an entity born inactive with a zero-length
    # closed row. Under the versioned contract the latest snapshot is always
    # open and its JSON `active` flag carries the state, so reopen the newest
    # row only when an entity has no current version.
    for periods, foreign_key in (
        (user_periods, 'user_id'), (area_periods, 'area_id'),
        (role_periods, 'role_id'), (group_periods, 'group_id'),
    ):
        entity_ids = bind.execute(sa.select(periods.c[foreign_key]).distinct()).scalars().all()
        for entity_id in entity_ids:
            open_id = bind.scalar(sa.select(periods.c.id).where(
                periods.c[foreign_key] == entity_id,
                periods.c.active_until.is_(None),
            ))
            if open_id is None:
                latest_id = bind.scalar(sa.select(sa.func.max(periods.c.id)).where(
                    periods.c[foreign_key] == entity_id,
                ))
                bind.execute(periods.update().where(periods.c.id == latest_id).values(active_until=None))

    for name in period_names:
        with op.batch_alter_table(name, schema=_schema()) as batch:
            batch.alter_column('values', existing_type=sa.JSON(), nullable=False)


def downgrade() -> None:
    for name in (
        'group_activity_periods', 'role_activity_periods',
        'area_activity_periods', 'user_activity_periods',
    ):
        op.drop_column(name, 'values', schema=_schema())
