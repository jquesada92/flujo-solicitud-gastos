"""Add permissions inherited by roles from their group.

Revision ID: 20260824_0009
Revises: 20260821_0008
"""

from alembic import op
import sqlalchemy as sa


revision = '20260824_0009'
down_revision = '20260821_0008'
branch_labels = None
depends_on = None


def _schema() -> str | None:
    return op.get_context().config.attributes.get('database_schema')


def _fk(table: str, column: str):
    schema = _schema()
    target = f'{schema}.{table}.{column}' if schema else f'{table}.{column}'
    return sa.ForeignKey(target, ondelete='CASCADE')


def _table(name: str, metadata: sa.MetaData, bind) -> sa.Table:
    return sa.Table(name, metadata, schema=_schema(), autoload_with=bind)


def _qualified(name: str) -> str:
    bind = op.get_bind()
    quote = bind.dialect.identifier_preparer.quote
    schema = _schema()
    return f'{quote(schema)}.{quote(name)}' if schema else quote(name)


def _backfill_open_activity_snapshots_offline() -> None:
    """Emit the data migration when Alembic has no inspectable connection."""
    dialect = op.get_bind().dialect.name
    role_periods = _qualified('role_activity_periods')
    group_periods = _qualified('group_activity_periods')
    role_permissions = _qualified('role_permissions')
    permissions = _qualified('permissions')

    if dialect == 'postgresql':
        op.execute(sa.text(f'''
            UPDATE {role_periods} AS period
            SET "values" = jsonb_set(
                COALESCE(period."values"::jsonb, '{{}}'::jsonb),
                '{{permission_codes}}',
                COALESCE((
                    SELECT jsonb_agg(permission_row.code ORDER BY permission_row.code)
                    FROM {role_permissions} AS assignment
                    JOIN {permissions} AS permission_row
                      ON permission_row.id = assignment.permission_id
                    WHERE assignment.role_id = period.role_id
                ), '[]'::jsonb),
                true
            )::json
            WHERE period.active_until IS NULL
        '''))
        op.execute(sa.text(f'''
            UPDATE {group_periods} AS period
            SET "values" = jsonb_set(
                COALESCE(period."values"::jsonb, '{{}}'::jsonb),
                '{{permission_codes}}',
                '[]'::jsonb,
                true
            )::json
            WHERE period.active_until IS NULL
        '''))
        return

    if dialect == 'sqlite':
        op.execute(sa.text(f'''
            UPDATE {role_periods} AS period
            SET "values" = json_set(
                COALESCE(period."values", '{{}}'),
                '$.permission_codes',
                json(COALESCE((
                    SELECT json_group_array(permission_code)
                    FROM (
                        SELECT permission_row.code AS permission_code
                        FROM {role_permissions} AS assignment
                        JOIN {permissions} AS permission_row
                          ON permission_row.id = assignment.permission_id
                        WHERE assignment.role_id = period.role_id
                        ORDER BY permission_row.code
                    ) AS ordered_permissions
                ), '[]'))
            )
            WHERE period.active_until IS NULL
        '''))
        op.execute(sa.text(f'''
            UPDATE {group_periods} AS period
            SET "values" = json_set(
                COALESCE(period."values", '{{}}'),
                '$.permission_codes',
                json('[]')
            )
            WHERE period.active_until IS NULL
        '''))
        return

    raise RuntimeError(f'Offline group permission migration is unsupported for dialect {dialect}')


def _backfill_open_activity_snapshots() -> None:
    """Align open temporal snapshots with the permission-aware runtime shape."""
    if op.get_context().as_sql:
        _backfill_open_activity_snapshots_offline()
        return

    bind = op.get_bind()
    metadata = sa.MetaData()
    role_periods = _table('role_activity_periods', metadata, bind)
    group_periods = _table('group_activity_periods', metadata, bind)
    role_permissions = _table('role_permissions', metadata, bind)
    permissions = _table('permissions', metadata, bind)

    open_role_periods = bind.execute(
        sa.select(role_periods.c.id, role_periods.c.role_id, role_periods.c['values'])
        .where(role_periods.c.active_until.is_(None))
    ).mappings().all()
    for period in open_role_periods:
        codes = list(bind.scalars(
            sa.select(permissions.c.code)
            .join(role_permissions, role_permissions.c.permission_id == permissions.c.id)
            .where(role_permissions.c.role_id == period['role_id'])
            .order_by(permissions.c.code)
        ))
        values = dict(period['values'] or {})
        values['permission_codes'] = codes
        bind.execute(
            role_periods.update()
            .where(role_periods.c.id == period['id'])
            .values(values=values)
        )

    open_group_periods = bind.execute(
        sa.select(group_periods.c.id, group_periods.c['values'])
        .where(group_periods.c.active_until.is_(None))
    ).mappings().all()
    for period in open_group_periods:
        values = dict(period['values'] or {})
        values['permission_codes'] = []
        bind.execute(
            group_periods.update()
            .where(group_periods.c.id == period['id'])
            .values(values=values)
        )


def _remove_permission_codes_from_activity_snapshots_offline() -> None:
    dialect = op.get_bind().dialect.name
    role_periods = _qualified('role_activity_periods')
    group_periods = _qualified('group_activity_periods')

    if dialect == 'postgresql':
        for periods in (role_periods, group_periods):
            op.execute(sa.text(f'''
                UPDATE {periods} AS period
                SET "values" = (
                    COALESCE(period."values"::jsonb, '{{}}'::jsonb)
                    - 'permission_codes'
                )::json
                WHERE period."values"::jsonb ? 'permission_codes'
            '''))
        return

    if dialect == 'sqlite':
        for periods in (role_periods, group_periods):
            op.execute(sa.text(f'''
                UPDATE {periods}
                SET "values" = json_remove(
                    COALESCE("values", '{{}}'),
                    '$.permission_codes'
                )
                WHERE json_type("values", '$.permission_codes') IS NOT NULL
            '''))
        return

    raise RuntimeError(f'Offline group permission downgrade is unsupported for dialect {dialect}')


def _remove_permission_codes_from_activity_snapshots() -> None:
    if op.get_context().as_sql:
        _remove_permission_codes_from_activity_snapshots_offline()
        return

    bind = op.get_bind()
    metadata = sa.MetaData()
    for table_name in ('role_activity_periods', 'group_activity_periods'):
        periods = _table(table_name, metadata, bind)
        rows = bind.execute(sa.select(periods.c.id, periods.c['values'])).mappings().all()
        for row in rows:
            values = dict(row['values'] or {})
            if 'permission_codes' not in values:
                continue
            values.pop('permission_codes')
            bind.execute(
                periods.update()
                .where(periods.c.id == row['id'])
                .values(values=values)
            )


def upgrade() -> None:
    schema = _schema()
    op.create_table(
        'group_permissions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('group_id', sa.Integer(), _fk('user_groups', 'id'), nullable=False),
        sa.Column('permission_id', sa.Integer(), _fk('permissions', 'id'), nullable=False),
        sa.UniqueConstraint('group_id', 'permission_id', name='uq_group_permission'),
        schema=schema,
    )
    op.create_index(
        'ix_group_permissions_group_id',
        'group_permissions',
        ['group_id'],
        schema=schema,
    )
    op.create_index(
        'ix_group_permissions_permission_id',
        'group_permissions',
        ['permission_id'],
        schema=schema,
    )
    _backfill_open_activity_snapshots()


def downgrade() -> None:
    _remove_permission_codes_from_activity_snapshots()
    op.drop_table('group_permissions', schema=_schema())
