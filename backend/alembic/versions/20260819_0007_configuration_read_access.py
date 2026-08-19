"""Add database-driven read-only configuration access.

Revision ID: 20260819_0007
Revises: 20260818_0006
Create Date: 2026-08-19

The product previously had only config:manage, which is intentionally restricted
to the protected system administrator. This revision introduces config:read as a
normal inheritable IAM capability and a neutral reusable viewer role.

For compatibility with the current PH deployment, the migration performs a
one-time assignment of that viewer role to active ordinary users who currently
receive requests:approve through the canonical IAM graph. This selects the
existing approval constituency from persisted relationships rather than Cargo,
Group, or Role names. It is a migration-time bootstrap only: future assignments
of configuration visibility are normal IAM data and are not inferred from
requests:approve at runtime.
"""

from alembic import op
import sqlalchemy as sa

revision = '20260819_0007'
down_revision = '20260818_0006'
branch_labels = None
depends_on = None


PERMISSION_CODE = 'config:read'
ROLE_CODE = 'configuration-viewer'


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    required = {
        'users',
        'permissions',
        'roles',
        'role_permissions',
        'user_role_assignments',
        'user_permissions',
        'group_members',
        'group_roles',
        'user_groups',
        'user_positions',
        'position_roles',
        'positions',
    }
    if not required <= tables:
        return

    bind.execute(sa.text('''
        INSERT INTO permissions (code, name, description, active)
        VALUES (
            :code,
            'Consultar configuración',
            'Consultar usuarios, organigrama, accesos, áreas, reglas y auditoría sin modificar la configuración.',
            TRUE
        )
        ON CONFLICT (code) DO UPDATE
        SET name = EXCLUDED.name,
            description = EXCLUDED.description,
            active = TRUE
    '''), {'code': PERMISSION_CODE})

    bind.execute(sa.text('''
        INSERT INTO roles (code, name, description, active, system_managed)
        VALUES (
            :role_code,
            'Visor de configuración',
            'Acceso de solo lectura a las pantallas de configuración. No concede permisos de modificación.',
            TRUE,
            FALSE
        )
        ON CONFLICT (code) DO UPDATE
        SET name = EXCLUDED.name,
            description = EXCLUDED.description,
            active = TRUE,
            system_managed = FALSE
    '''), {'role_code': ROLE_CODE})

    bind.execute(sa.text('''
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        JOIN permissions p ON p.code = :permission_code
        WHERE r.code = :role_code
        ON CONFLICT (role_id, permission_id) DO NOTHING
    '''), {'permission_code': PERMISSION_CODE, 'role_code': ROLE_CODE})

    system_filter = (
        'AND NOT EXISTS (SELECT 1 FROM system_accounts sa WHERE sa.user_id = u.id)'
        if 'system_accounts' in tables else ''
    )

    # One-time bootstrap from the *current* canonical approval constituency.
    # No organizational name is used here; after this migration, administrators
    # assign/remove the viewer role through IAM like any other persisted role.
    bind.execute(sa.text(f'''
        WITH approver_users AS (
            SELECT up.user_id
            FROM user_permissions up
            JOIN permissions p ON p.id = up.permission_id
            WHERE p.code = 'requests:approve' AND p.active = TRUE

            UNION

            SELECT ura.user_id
            FROM user_role_assignments ura
            JOIN roles assigned_role ON assigned_role.id = ura.role_id
            JOIN role_permissions rp ON rp.role_id = assigned_role.id
            JOIN permissions p ON p.id = rp.permission_id
            WHERE p.code = 'requests:approve'
              AND p.active = TRUE
              AND assigned_role.active = TRUE

            UNION

            SELECT gm.user_id
            FROM group_members gm
            JOIN user_groups ug ON ug.id = gm.group_id
            JOIN group_roles gr ON gr.group_id = ug.id
            JOIN roles assigned_role ON assigned_role.id = gr.role_id
            JOIN role_permissions rp ON rp.role_id = assigned_role.id
            JOIN permissions p ON p.id = rp.permission_id
            WHERE p.code = 'requests:approve'
              AND p.active = TRUE
              AND ug.active = TRUE
              AND assigned_role.active = TRUE

            UNION

            SELECT upos.user_id
            FROM user_positions upos
            JOIN positions pos ON pos.id = upos.position_id
            JOIN position_roles pr ON pr.position_id = pos.id
            JOIN roles assigned_role ON assigned_role.id = pr.role_id
            JOIN role_permissions rp ON rp.role_id = assigned_role.id
            JOIN permissions p ON p.id = rp.permission_id
            WHERE p.code = 'requests:approve'
              AND p.active = TRUE
              AND pos.active = TRUE
              AND assigned_role.active = TRUE
        )
        INSERT INTO user_role_assignments (user_id, role_id)
        SELECT au.user_id, viewer.id
        FROM approver_users au
        JOIN users u ON u.id = au.user_id
        CROSS JOIN roles viewer
        WHERE u.active = TRUE
          AND viewer.code = :role_code
          {system_filter}
        ON CONFLICT (user_id, role_id) DO NOTHING
    '''), {'role_code': ROLE_CODE})


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if {'user_role_assignments', 'roles'} <= tables:
        bind.execute(sa.text('''
            DELETE FROM user_role_assignments
            WHERE role_id IN (SELECT id FROM roles WHERE code = :role_code)
        '''), {'role_code': ROLE_CODE})
    if {'role_permissions', 'roles'} <= tables:
        bind.execute(sa.text('''
            DELETE FROM role_permissions
            WHERE role_id IN (SELECT id FROM roles WHERE code = :role_code)
        '''), {'role_code': ROLE_CODE})
    if 'roles' in tables:
        bind.execute(sa.text('DELETE FROM roles WHERE code = :role_code'), {'role_code': ROLE_CODE})
    if 'permissions' in tables:
        bind.execute(sa.text('DELETE FROM permissions WHERE code = :permission_code'), {'permission_code': PERMISSION_CODE})
