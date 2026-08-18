"""Allow configurable positions to inherit IAM roles.

Revision ID: 20260818_0004
Revises: 20260817_0003
Create Date: 2026-08-18

This migration adds the canonical Position -> Role relationship. It also performs
one one-time compatibility import from the legacy access_profiles/users.title
configuration so existing production titles such as Presidente, Vicepresidente
or Tesorero keep the permissions administrators already configured. Runtime
authorization does not read legacy profile names or can_* flags after migration.
"""

from alembic import op
import sqlalchemy as sa

revision = '20260818_0004'
down_revision = '20260817_0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    required = {'positions', 'roles', 'users'}
    if not required <= tables:
        return

    if 'position_roles' not in tables:
        op.create_table(
            'position_roles',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column(
                'position_id',
                sa.Integer(),
                sa.ForeignKey('positions.id', ondelete='CASCADE'),
                nullable=False,
            ),
            sa.Column(
                'role_id',
                sa.Integer(),
                sa.ForeignKey('roles.id', ondelete='CASCADE'),
                nullable=False,
            ),
            sa.UniqueConstraint('position_id', 'role_id', name='uq_position_role'),
        )
        op.create_index('ix_position_roles_position_id', 'position_roles', ['position_id'])
        op.create_index('ix_position_roles_role_id', 'position_roles', ['role_id'])

    tables = set(sa.inspect(bind).get_table_names())
    compatibility_tables = {
        'access_profiles',
        'permissions',
        'role_permissions',
        'user_positions',
    }
    if not compatibility_tables <= tables:
        return

    # 1) Promote each legacy access profile into a canonical Position when an
    # equivalent position does not already exist. Names remain organization data;
    # no specific title is required by runtime code.
    bind.execute(sa.text('''
        INSERT INTO positions (code, name, description, active)
        SELECT
            'legacy-' || lower(replace(ap.code, '_', '-')),
            ap.name,
            'Cargo migrado desde la configuración de acceso anterior.',
            ap.active
        FROM access_profiles ap
        WHERE NOT EXISTS (
            SELECT 1
            FROM positions p
            WHERE lower(p.name) = lower(ap.name)
               OR p.code = 'legacy-' || lower(replace(ap.code, '_', '-'))
        )
    '''))

    # 2) Materialize one reusable role per migrated profile. The role is only a
    # migration bridge; afterwards administrators can rename/change/remove it in
    # the regular IAM UI without relying on the legacy profile.
    bind.execute(sa.text('''
        INSERT INTO roles (code, name, description, active, system_managed)
        SELECT
            'legacy-position-' || lower(replace(ap.code, '_', '-')),
            'Acceso por cargo: ' || ap.name,
            'Rol migrado desde permisos legacy del cargo.',
            ap.active,
            FALSE
        FROM access_profiles ap
        ON CONFLICT (code) DO UPDATE
        SET active = EXCLUDED.active,
            description = EXCLUDED.description
    '''))

    mappings = (
        ('can_view', 'requests:read'),
        ('can_request', 'requests:create'),
        ('can_approve', 'requests:approve'),
        ('can_configure', 'config:manage'),
    )
    profile_columns = {
        column['name'] for column in sa.inspect(bind).get_columns('access_profiles')
    }
    for column_name, permission_code in mappings:
        if column_name not in profile_columns:
            continue
        bind.execute(sa.text(f'''
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM access_profiles ap
            JOIN roles r
              ON r.code = 'legacy-position-' || lower(replace(ap.code, '_', '-'))
            JOIN permissions p ON p.code = :permission_code
            WHERE ap.{column_name} = TRUE
            ON CONFLICT (role_id, permission_id) DO NOTHING
        '''), {'permission_code': permission_code})

    # Historical compatibility only: the old ADMINISTRADORA profile carried the
    # closure responsibility through a one-time migration in 0001. Preserve that
    # capability at position level without making the name a runtime condition.
    bind.execute(sa.text('''
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM access_profiles ap
        JOIN roles r
          ON r.code = 'legacy-position-' || lower(replace(ap.code, '_', '-'))
        JOIN permissions p ON p.code = 'requests:close'
        WHERE ap.code = 'ADMINISTRADORA'
        ON CONFLICT (role_id, permission_id) DO NOTHING
    '''))

    # 3) Link each canonical Position to its migrated role. If an administrator
    # already created an equivalent position by name, reuse it.
    bind.execute(sa.text('''
        INSERT INTO position_roles (position_id, role_id)
        SELECT
            (
                SELECT p.id
                FROM positions p
                WHERE lower(p.name) = lower(ap.name)
                   OR p.code = 'legacy-' || lower(replace(ap.code, '_', '-'))
                ORDER BY CASE WHEN lower(p.name) = lower(ap.name) THEN 0 ELSE 1 END, p.id
                LIMIT 1
            ),
            r.id
        FROM access_profiles ap
        JOIN roles r
          ON r.code = 'legacy-position-' || lower(replace(ap.code, '_', '-'))
        WHERE EXISTS (
            SELECT 1
            FROM positions p
            WHERE lower(p.name) = lower(ap.name)
               OR p.code = 'legacy-' || lower(replace(ap.code, '_', '-'))
        )
        ON CONFLICT (position_id, role_id) DO NOTHING
    '''))

    # 4) Assign existing non-system users to the canonical Position that matches
    # their legacy title code. This converts current production configuration into
    # normal IAM data. Future assignments should use user_positions directly.
    system_filter = (
        'AND NOT EXISTS (SELECT 1 FROM system_accounts sa WHERE sa.user_id = u.id)'
        if 'system_accounts' in tables else ''
    )
    bind.execute(sa.text(f'''
        INSERT INTO user_positions (user_id, position_id)
        SELECT
            u.id,
            (
                SELECT p.id
                FROM positions p
                WHERE lower(p.name) = lower(ap.name)
                   OR p.code = 'legacy-' || lower(replace(ap.code, '_', '-'))
                ORDER BY CASE WHEN lower(p.name) = lower(ap.name) THEN 0 ELSE 1 END, p.id
                LIMIT 1
            )
        FROM users u
        JOIN access_profiles ap ON ap.code = u.title
        WHERE u.active = TRUE
          {system_filter}
        ON CONFLICT (user_id, position_id) DO NOTHING
    '''))


def downgrade() -> None:
    # The compatibility import may have been edited through the IAM UI after the
    # upgrade, so roles/positions/user assignments are not deleted automatically.
    # Only remove the structural relationship introduced by this revision.
    bind = op.get_bind()
    if 'position_roles' in set(sa.inspect(bind).get_table_names()):
        op.drop_table('position_roles')
