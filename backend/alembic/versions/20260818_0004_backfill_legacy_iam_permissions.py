"""Backfill legacy operational flags into canonical IAM permissions.

Revision ID: 20260818_0004
Revises: 20260817_0003
Create Date: 2026-08-18

This is a one-time compatibility migration for users created or edited through
legacy user/profile screens after the IAM foundation migration had already run.
Runtime authorization continues to use canonical IAM only.
"""

from alembic import op
import sqlalchemy as sa

revision = '20260818_0004'
down_revision = '20260817_0003'
branch_labels = None
depends_on = None


LEGACY_MAPPINGS = (
    ('can_request', 'requests:create'),
    ('can_approve', 'requests:approve'),
    ('can_configure', 'config:manage'),
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    required = {'users', 'permissions', 'user_permissions'}
    if not required <= tables:
        return

    user_columns = {column['name'] for column in inspector.get_columns('users')}
    has_system_accounts = 'system_accounts' in tables
    system_filter = (
        'AND NOT EXISTS (SELECT 1 FROM system_accounts sa WHERE sa.user_id = u.id)'
        if has_system_accounts
        else "AND u.role::text <> 'ADMIN'"
    )

    for column_name, permission_code in LEGACY_MAPPINGS:
        if column_name not in user_columns:
            continue
        bind.execute(sa.text(f'''
            INSERT INTO user_permissions (user_id, permission_id)
            SELECT u.id, p.id
            FROM users u
            JOIN permissions p ON p.code = :permission_code AND p.active = TRUE
            WHERE u.active = TRUE
              AND u.{column_name} = TRUE
              {system_filter}
            ON CONFLICT (user_id, permission_id) DO NOTHING
        '''), {'permission_code': permission_code})

    # PH-only compatibility for records created after IAM 0001. This mapping is
    # migration input, never runtime authorization. Future organizations assign
    # requests:close from the IAM configuration UI.
    if 'title' in user_columns:
        bind.execute(sa.text(f'''
            INSERT INTO user_permissions (user_id, permission_id)
            SELECT u.id, p.id
            FROM users u
            JOIN permissions p ON p.code = 'requests:close' AND p.active = TRUE
            WHERE u.active = TRUE
              AND u.title = 'ADMINISTRADORA'
              {system_filter}
            ON CONFLICT (user_id, permission_id) DO NOTHING
        '''))


def downgrade() -> None:
    # Additive compatibility backfills cannot be safely distinguished from
    # legitimate direct IAM grants. Downgrade intentionally preserves access
    # assignments instead of deleting potentially valid authorization data.
    pass
