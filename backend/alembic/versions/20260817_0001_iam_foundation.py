"""Configurable IAM foundation.

Revision ID: 20260817_0001
Revises: 20260817_0000
Create Date: 2026-08-17

This migration intentionally contains one-time compatibility mappings from the
legacy MVP. Runtime authorization must not depend on these names afterwards.
"""

from alembic import op
import sqlalchemy as sa

revision = '20260817_0001'
down_revision = '20260817_0000'
branch_labels = None
depends_on = None


PERMISSIONS = (
    ('requests:read', 'Consultar solicitudes', 'Consultar solicitudes y documentos autorizados.'),
    ('requests:create', 'Crear solicitudes', 'Crear, corregir y administrar solicitudes propias abiertas.'),
    ('requests:approve', 'Aprobar solicitudes', 'Votar, aprobar, rechazar o solicitar corrección.'),
    ('requests:close', 'Cerrar solicitudes', 'Subir o reemplazar factura y cerrar solicitudes aprobadas.'),
    ('config:manage', 'Administrar configuración', 'Administrar usuarios, grupos, roles, cargos y configuración.'),
)


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    existing = _tables()

    if 'permissions' not in existing:
        op.create_table(
            'permissions',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('code', sa.String(length=100), nullable=False),
            sa.Column('name', sa.String(length=150), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint('code', name='uq_permissions_code'),
        )
        op.create_index('ix_permissions_code', 'permissions', ['code'], unique=True)

    if 'roles' not in existing:
        op.create_table(
            'roles',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('code', sa.String(length=100), nullable=False),
            sa.Column('name', sa.String(length=150), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('system_managed', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint('code', name='uq_roles_code'),
            sa.UniqueConstraint('name', name='uq_roles_name'),
        )
        op.create_index('ix_roles_code', 'roles', ['code'], unique=True)

    if 'role_permissions' not in existing:
        op.create_table(
            'role_permissions',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('role_id', sa.Integer(), sa.ForeignKey('roles.id', ondelete='CASCADE'), nullable=False),
            sa.Column('permission_id', sa.Integer(), sa.ForeignKey('permissions.id', ondelete='CASCADE'), nullable=False),
            sa.UniqueConstraint('role_id', 'permission_id', name='uq_role_permission'),
        )
        op.create_index('ix_role_permissions_role_id', 'role_permissions', ['role_id'])
        op.create_index('ix_role_permissions_permission_id', 'role_permissions', ['permission_id'])

    if 'user_groups' not in existing:
        op.create_table(
            'user_groups',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('code', sa.String(length=100), nullable=False),
            sa.Column('name', sa.String(length=150), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint('code', name='uq_user_groups_code'),
            sa.UniqueConstraint('name', name='uq_user_groups_name'),
        )
        op.create_index('ix_user_groups_code', 'user_groups', ['code'], unique=True)

    if 'group_members' not in existing:
        op.create_table(
            'group_members',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('group_id', sa.Integer(), sa.ForeignKey('user_groups.id', ondelete='CASCADE'), nullable=False),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.UniqueConstraint('group_id', 'user_id', name='uq_group_member'),
        )
        op.create_index('ix_group_members_group_id', 'group_members', ['group_id'])
        op.create_index('ix_group_members_user_id', 'group_members', ['user_id'])

    if 'group_roles' not in existing:
        op.create_table(
            'group_roles',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('group_id', sa.Integer(), sa.ForeignKey('user_groups.id', ondelete='CASCADE'), nullable=False),
            sa.Column('role_id', sa.Integer(), sa.ForeignKey('roles.id', ondelete='CASCADE'), nullable=False),
            sa.UniqueConstraint('group_id', 'role_id', name='uq_group_role'),
        )
        op.create_index('ix_group_roles_group_id', 'group_roles', ['group_id'])
        op.create_index('ix_group_roles_role_id', 'group_roles', ['role_id'])

    if 'user_role_assignments' not in existing:
        op.create_table(
            'user_role_assignments',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('role_id', sa.Integer(), sa.ForeignKey('roles.id', ondelete='CASCADE'), nullable=False),
            sa.UniqueConstraint('user_id', 'role_id', name='uq_user_role_assignment'),
        )
        op.create_index('ix_user_role_assignments_user_id', 'user_role_assignments', ['user_id'])
        op.create_index('ix_user_role_assignments_role_id', 'user_role_assignments', ['role_id'])

    if 'user_permissions' not in existing:
        op.create_table(
            'user_permissions',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('permission_id', sa.Integer(), sa.ForeignKey('permissions.id', ondelete='CASCADE'), nullable=False),
            sa.UniqueConstraint('user_id', 'permission_id', name='uq_user_permission'),
        )
        op.create_index('ix_user_permissions_user_id', 'user_permissions', ['user_id'])
        op.create_index('ix_user_permissions_permission_id', 'user_permissions', ['permission_id'])

    if 'positions' not in existing:
        op.create_table(
            'positions',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('code', sa.String(length=100), nullable=False),
            sa.Column('name', sa.String(length=150), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint('code', name='uq_positions_code'),
            sa.UniqueConstraint('name', name='uq_positions_name'),
        )
        op.create_index('ix_positions_code', 'positions', ['code'], unique=True)

    if 'user_positions' not in existing:
        op.create_table(
            'user_positions',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('position_id', sa.Integer(), sa.ForeignKey('positions.id', ondelete='CASCADE'), nullable=False),
            sa.UniqueConstraint('user_id', 'position_id', name='uq_user_position'),
        )
        op.create_index('ix_user_positions_user_id', 'user_positions', ['user_id'])
        op.create_index('ix_user_positions_position_id', 'user_positions', ['position_id'])

    bind = op.get_bind()
    for code, name, description in PERMISSIONS:
        bind.execute(sa.text('''
            INSERT INTO permissions (code, name, description, active)
            VALUES (:code, :name, :description, TRUE)
            ON CONFLICT (code) DO UPDATE
            SET name = EXCLUDED.name,
                description = EXCLUDED.description,
                active = TRUE
        '''), {'code': code, 'name': name, 'description': description})

    bind.execute(sa.text('''
        INSERT INTO roles (code, name, description, active, system_managed)
        VALUES (
            'system-administrator',
            'Administrador del sistema',
            'Rol técnico de bootstrap. No participa en el flujo financiero.',
            TRUE,
            TRUE
        )
        ON CONFLICT (code) DO UPDATE
        SET name = EXCLUDED.name,
            description = EXCLUDED.description,
            active = TRUE,
            system_managed = TRUE
    '''))

    bind.execute(sa.text('''
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        JOIN permissions p ON p.code IN ('config:manage', 'requests:read')
        WHERE r.code = 'system-administrator'
        ON CONFLICT (role_id, permission_id) DO NOTHING
    '''))

    # Existing technical administrators are deliberately restricted to
    # configuration + consultation. Legacy can_* flags are ignored thereafter.
    bind.execute(sa.text('''
        INSERT INTO user_role_assignments (user_id, role_id)
        SELECT u.id, r.id
        FROM users u
        CROSS JOIN roles r
        WHERE u.role::text = 'ADMIN'
          AND r.code = 'system-administrator'
        ON CONFLICT (user_id, role_id) DO NOTHING
    '''))

    # One-time migration of legacy access flags for non-system users. These
    # column names are compatibility input only and are not runtime authority.
    legacy_columns = {column['name'] for column in sa.inspect(bind).get_columns('users')}
    if {'can_view', 'can_request', 'can_approve', 'can_configure'} <= legacy_columns:
        mappings = (
            ('can_view', 'requests:read'),
            ('can_request', 'requests:create'),
            ('can_approve', 'requests:approve'),
            ('can_configure', 'config:manage'),
        )
        for column_name, permission_code in mappings:
            bind.execute(sa.text(f'''
                INSERT INTO user_permissions (user_id, permission_id)
                SELECT u.id, p.id
                FROM users u
                JOIN permissions p ON p.code = :permission_code
                WHERE u.role::text <> 'ADMIN'
                  AND u.{column_name} = TRUE
                ON CONFLICT (user_id, permission_id) DO NOTHING
            '''), {'permission_code': permission_code})

    # Legacy PH compatibility only: the old ADMINISTRADORA profile was the
    # actor responsible for invoices/closure. Future organizations configure
    # this permission through the UI instead of relying on this title.
    if 'title' in legacy_columns:
        bind.execute(sa.text('''
            INSERT INTO user_permissions (user_id, permission_id)
            SELECT u.id, p.id
            FROM users u
            JOIN permissions p ON p.code = 'requests:close'
            WHERE u.role::text <> 'ADMIN'
              AND u.title = 'ADMINISTRADORA'
            ON CONFLICT (user_id, permission_id) DO NOTHING
        '''))


def downgrade() -> None:
    for table in (
        'user_positions',
        'positions',
        'user_permissions',
        'user_role_assignments',
        'group_roles',
        'group_members',
        'user_groups',
        'role_permissions',
        'roles',
        'permissions',
    ):
        op.drop_table(table)
