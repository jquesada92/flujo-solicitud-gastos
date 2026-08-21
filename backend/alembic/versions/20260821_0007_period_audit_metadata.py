"""Add actor and change metadata to temporal versions.

Revision ID: 20260821_0007
Revises: 20260821_0006
"""

from alembic import op
import sqlalchemy as sa


revision = '20260821_0007'
down_revision = '20260821_0006'
branch_labels = None
depends_on = None


def _schema() -> str | None:
    return op.get_context().config.attributes.get('database_schema')


def upgrade() -> None:
    schema = _schema()
    tables = (
        'user_activity_periods', 'area_activity_periods',
        'role_activity_periods', 'group_activity_periods',
    )
    for table in tables:
        op.add_column(table, sa.Column('event_at', sa.DateTime(timezone=True), nullable=True), schema=schema)
        op.add_column(table, sa.Column('actor_user_id', sa.Integer(), nullable=True), schema=schema)
        op.add_column(table, sa.Column('actor_identifier', sa.String(255), nullable=True), schema=schema)
        op.add_column(table, sa.Column('actor_identity_document', sa.String(50), nullable=True), schema=schema)
        op.add_column(table, sa.Column('change_type', sa.String(40), nullable=True), schema=schema)
        op.add_column(table, sa.Column('changed_fields', sa.JSON(), nullable=True), schema=schema)
        op.add_column(table, sa.Column('changes', sa.JSON(), nullable=True), schema=schema)
        op.create_foreign_key(
            f'fk_{table}_actor_user_id_users', table, 'users',
            ['actor_user_id'], ['id'], source_schema=schema, referent_schema=schema,
            ondelete='SET NULL',
        )
        op.create_index(f'ix_{table}_actor_user_id', table, ['actor_user_id'], schema=schema)

    metadata = sa.MetaData()
    for table_name in tables:
        table = sa.Table(table_name, metadata, schema=schema, autoload_with=op.get_bind())
        rows = op.get_bind().execute(sa.select(table.c.id, table.c.active_from, table.c['values'])).mappings()
        for row in rows:
            snapshot = row['values'] or {}
            changes = {key: {'before': None, 'after': value} for key, value in snapshot.items()}
            op.get_bind().execute(table.update().where(table.c.id == row['id']).values(
                event_at=row['active_from'],
                actor_identifier='SYSTEM:MIGRATION_BACKFILL',
                change_type='BACKFILL',
                changed_fields=sorted(snapshot),
                changes=changes,
            ))
        with op.batch_alter_table(table_name, schema=schema) as batch:
            batch.alter_column('event_at', existing_type=sa.DateTime(timezone=True), nullable=False)
            batch.alter_column('actor_identifier', existing_type=sa.String(255), nullable=False)
            batch.alter_column('change_type', existing_type=sa.String(40), nullable=False)
            batch.alter_column('changed_fields', existing_type=sa.JSON(), nullable=False)
            batch.alter_column('changes', existing_type=sa.JSON(), nullable=False)


def downgrade() -> None:
    schema = _schema()
    for table in (
        'group_activity_periods', 'role_activity_periods',
        'area_activity_periods', 'user_activity_periods',
    ):
        op.drop_index(f'ix_{table}_actor_user_id', table_name=table, schema=schema)
        op.drop_constraint(f'fk_{table}_actor_user_id_users', table, schema=schema, type_='foreignkey')
        for column in (
            'changes', 'changed_fields', 'change_type', 'actor_identity_document',
            'actor_identifier', 'actor_user_id', 'event_at',
        ):
            op.drop_column(table, column, schema=schema)
