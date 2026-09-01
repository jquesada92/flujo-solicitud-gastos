"""Retire audit tables replaced by the canonical change feed.

Revision ID: 20260831_0016
Revises: 20260831_0015

This migration is intentionally irreversible.  Every legacy row is retained in
``audit_change_feed`` with its original source key before the physical tables
are removed.  Restoring the previous layout requires a pre-cutover database
backup and the previous application image; recreating empty history tables
would provide false assurance.
"""

from alembic import op
import sqlalchemy as sa


revision = '20260831_0016'
down_revision = '20260831_0015'
branch_labels = None
depends_on = None


RETIRED_TABLES = (
    'invoice_change_events',
    'approval_policy_change_events',
    'access_profile_change_events',
    'user_change_events',
    'group_activity_periods',
    'role_activity_periods',
    'area_activity_periods',
    'user_activity_periods',
)


def _schema() -> str | None:
    return op.get_context().config.attributes.get('database_schema')


def _qualified(bind, table: str) -> str:
    preparer = bind.dialect.identifier_preparer
    quoted_table = preparer.quote(table)
    schema = _schema()
    return f'{preparer.quote(schema)}.{quoted_table}' if schema else quoted_table


def _assert_complete_copy(bind) -> None:
    if bind.dialect.name != 'postgresql':
        return
    feed = _qualified(bind, 'audit_change_feed')
    locked_sources = ', '.join(_qualified(bind, table) for table in RETIRED_TABLES)
    bind.exec_driver_sql(f'LOCK TABLE {locked_sources} IN ACCESS EXCLUSIVE MODE')
    for table in RETIRED_TABLES:
        source = _qualified(bind, table)
        expected = bind.scalar(sa.text(f'SELECT count(*) FROM {source}')) or 0
        actual = bind.scalar(
            sa.text(f'SELECT count(*) FROM {feed} WHERE source_type = :source_type'),
            {'source_type': table},
        ) or 0
        if expected != actual:
            raise RuntimeError(
                f'Refusing to drop {table}: change-feed copy has {actual} '
                f'rows but source has {expected}'
            )


def upgrade() -> None:
    bind = op.get_bind()
    _assert_complete_copy(bind)
    for table in RETIRED_TABLES:
        # Deliberately no CASCADE: PostgreSQL must abort if an uninventoryed
        # consumer still depends on one of these sources.
        op.drop_table(table, schema=_schema())


def downgrade() -> None:
    raise RuntimeError(
        'Irreversible audit consolidation: restore the pre-cutover database '
        'backup and deploy the previous application image.'
    )
