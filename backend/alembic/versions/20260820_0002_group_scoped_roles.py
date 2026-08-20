"""Bind every business role to one group and one role per user/group.

Revision ID: 20260820_0002
Revises: 20260820_0001
Create Date: 2026-08-20

The existing GroupRole table becomes the canonical role -> group binding. Group
membership is derived from a user's role assignment instead of being an
independent authorization grant.
"""

from alembic import context, op
import sqlalchemy as sa


revision = '20260820_0002'
down_revision = '20260820_0001'
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
    group_roles = _qualified(schema, 'group_roles')
    assignments = _qualified(schema, 'user_role_assignments')
    members = _qualified(schema, 'group_members')

    # Previous design allowed the same role to be attached to several groups.
    # Keep one deterministic binding before adding the database constraint.
    op.execute(sa.text(
        f'DELETE FROM {group_roles} '
        f'WHERE id NOT IN (SELECT MIN(id) FROM {group_roles} GROUP BY role_id)'
    ))

    with op.batch_alter_table('group_roles', schema=schema) as batch:
        batch.create_unique_constraint('uq_group_role_role', ['role_id'])

    # A direct role without a group is invalid in the new model. If old test
    # data contains duplicates within the same group, retain the oldest row.
    op.execute(sa.text(
        f'DELETE FROM {assignments} AS ura '
        f'WHERE NOT EXISTS (SELECT 1 FROM {group_roles} gr WHERE gr.role_id = ura.role_id) '
        f'OR EXISTS ('
        f'  SELECT 1 FROM {assignments} ura2 '
        f'  JOIN {group_roles} gr2 ON gr2.role_id = ura2.role_id '
        f'  JOIN {group_roles} gr1 ON gr1.role_id = ura.role_id '
        f'  WHERE ura2.user_id = ura.user_id '
        f'    AND gr2.group_id = gr1.group_id '
        f'    AND ura2.id < ura.id'
        f')'
    ))

    # Membership is now a projection of role assignments. Rebuild it once so
    # pre-existing test data matches the new invariant immediately.
    op.execute(sa.text(f'DELETE FROM {members}'))
    op.execute(sa.text(
        f'INSERT INTO {members} (group_id, user_id) '
        f'SELECT DISTINCT gr.group_id, ura.user_id '
        f'FROM {assignments} ura JOIN {group_roles} gr ON gr.role_id = ura.role_id'
    ))

    # PostgreSQL gets a database-level guard for the cross-table invariant that
    # a user may own at most one role inside a group. SQLite remains protected
    # by the backend validation used by local/unit-test environments.
    if bind.dialect.name == 'postgresql':
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
        op.execute(sa.text(f'''
            CREATE TRIGGER trg_user_role_one_per_group
            BEFORE INSERT OR UPDATE OF user_id, role_id ON {assignments}
            FOR EACH ROW EXECUTE FUNCTION {function_name}();
        '''))


def downgrade() -> None:
    bind = op.get_bind()
    schema = _configured_schema(bind)
    assignments = _qualified(schema, 'user_role_assignments')

    if bind.dialect.name == 'postgresql':
        prefix = f'"{schema}".' if schema else ''
        op.execute(sa.text(f'DROP TRIGGER IF EXISTS trg_user_role_one_per_group ON {assignments}'))
        op.execute(sa.text(f'DROP FUNCTION IF EXISTS {prefix}enforce_user_role_group_assignment()'))

    with op.batch_alter_table('group_roles', schema=schema) as batch:
        batch.drop_constraint('uq_group_role_role', type_='unique')
