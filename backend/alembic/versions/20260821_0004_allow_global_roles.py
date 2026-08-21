"""Allow global roles without removing one-role-per-group protection.

Revision ID: 20260821_0004
Revises: 20260821_0003
Create Date: 2026-08-21

A role may belong to zero or one group. Roles with no GroupRole binding are
Global Roles and may be assigned directly through the canonical user access
payload. Group membership continues to be derived only from grouped roles.
"""

from alembic import context, op
import sqlalchemy as sa


revision = '20260821_0004'
down_revision = '20260821_0003'
branch_labels = None
depends_on = None


def _configured_schema(bind) -> str | None:
    if bind.dialect.name == 'sqlite':
        return None
    schema = context.config.attributes.get('database_schema')
    if not schema:
        raise RuntimeError('DATABASE_SCHEMA must be configured for PostgreSQL migrations')
    return schema


def _qualified(schema: str | None, table: str) -> str:
    return f'"{schema}"."{table}"' if schema else f'"{table}"'


def upgrade() -> None:
    bind = op.get_bind()
    schema = _configured_schema(bind)
    if bind.dialect.name != 'postgresql':
        return

    group_roles = _qualified(schema, 'group_roles')
    assignments = _qualified(schema, 'user_role_assignments')
    prefix = f'"{schema}".' if schema else ''
    function_name = f'{prefix}enforce_user_role_group_assignment'

    # Keep the existing trigger name from 0002 and replace only its function.
    # A missing group now means a valid global role; grouped roles retain the
    # cross-table one-role-per-user/group invariant.
    op.execute(sa.text(f'''
        CREATE OR REPLACE FUNCTION {function_name}()
        RETURNS trigger AS $$
        DECLARE
            target_group_id integer;
        BEGIN
            SELECT group_id INTO target_group_id
            FROM {group_roles}
            WHERE role_id = NEW.role_id;

            IF target_group_id IS NULL THEN
                RETURN NEW;
            END IF;

            IF EXISTS (
                SELECT 1
                FROM {assignments} existing
                JOIN {group_roles} existing_group
                  ON existing_group.role_id = existing.role_id
                WHERE existing.user_id = NEW.user_id
                  AND existing_group.group_id = target_group_id
                  AND existing.id <> COALESCE(NEW.id, -1)
            ) THEN
                RAISE EXCEPTION 'A user can only have one role per group';
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    '''))


def downgrade() -> None:
    bind = op.get_bind()
    schema = _configured_schema(bind)
    group_roles = _qualified(schema, 'group_roles')
    assignments = _qualified(schema, 'user_role_assignments')

    # The previous contract did not allow ungrouped role assignments.
    op.execute(sa.text(
        f'DELETE FROM {assignments} AS ura '
        f'WHERE NOT EXISTS (SELECT 1 FROM {group_roles} gr WHERE gr.role_id = ura.role_id)'
    ))

    if bind.dialect.name != 'postgresql':
        return

    prefix = f'"{schema}".' if schema else ''
    function_name = f'{prefix}enforce_user_role_group_assignment'
    op.execute(sa.text(f'''
        CREATE OR REPLACE FUNCTION {function_name}()
        RETURNS trigger AS $$
        DECLARE
            target_group_id integer;
        BEGIN
            SELECT group_id INTO target_group_id
            FROM {group_roles}
            WHERE role_id = NEW.role_id;

            IF target_group_id IS NULL THEN
                RAISE EXCEPTION 'The selected role is not bound to a group';
            END IF;

            IF EXISTS (
                SELECT 1
                FROM {assignments} existing
                JOIN {group_roles} existing_group
                  ON existing_group.role_id = existing.role_id
                WHERE existing.user_id = NEW.user_id
                  AND existing_group.group_id = target_group_id
                  AND existing.id <> COALESCE(NEW.id, -1)
            ) THEN
                RAISE EXCEPTION 'A user can only have one role per group';
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    '''))
