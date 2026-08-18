"""Separate area configuration from technical system administration.

Revision ID: 20260818_0006
Revises: 20260818_0005
Create Date: 2026-08-18

``areas:manage`` is an organization-neutral permission that can be inherited by
ordinary users through configurable Roles, Groups or Positions. ``config:manage``
is reserved at runtime for protected ``system_accounts`` and is never granted by
matching a user/group/position name.
"""

from alembic import op
import sqlalchemy as sa

revision = '20260818_0006'
down_revision = '20260818_0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if 'permissions' not in tables:
        return

    bind.execute(sa.text('''
        INSERT INTO permissions (code, name, description, active)
        VALUES (
            'areas:manage',
            'Administrar áreas',
            'Crear, editar, activar/desactivar Áreas y administrar sus Categorías asociadas.',
            TRUE
        )
        ON CONFLICT (code) DO UPDATE
        SET name = EXCLUDED.name,
            description = EXCLUDED.description,
            active = TRUE
    '''))

    bind.execute(sa.text('''
        UPDATE permissions
        SET name = 'Administración técnica del sistema',
            description = 'Reservado a system_accounts: Usuarios, Organigrama, Accesos, reglas y auditoría técnica.'
        WHERE code = 'config:manage'
    '''))

    # Seed a neutral reusable role. It is intentionally NOT assigned to any
    # named group/cargo here; organizational membership remains configuration.
    if {'roles', 'role_permissions'} <= tables:
        role_id = bind.execute(sa.text('''
            SELECT id FROM roles WHERE code = 'area-manager'
        ''')).scalar()
        if role_id is None:
            role_id = bind.execute(sa.text('''
                INSERT INTO roles (code, name, description, active, system_managed)
                VALUES (
                    'area-manager',
                    'Gestor de áreas',
                    'Administra el catálogo de Áreas y sus Categorías asociadas.',
                    TRUE,
                    FALSE
                )
                RETURNING id
            ''')).scalar_one()

        permission_id = bind.execute(sa.text('''
            SELECT id FROM permissions WHERE code = 'areas:manage'
        ''')).scalar_one()
        bind.execute(sa.text('''
            INSERT INTO role_permissions (role_id, permission_id)
            VALUES (:role_id, :permission_id)
            ON CONFLICT DO NOTHING
        '''), {'role_id': role_id, 'permission_id': permission_id})


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if 'permissions' in tables:
        bind.execute(sa.text('''
            UPDATE permissions
            SET active = FALSE
            WHERE code = 'areas:manage'
        '''))
