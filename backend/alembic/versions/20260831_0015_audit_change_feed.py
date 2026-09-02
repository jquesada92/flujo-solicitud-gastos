"""Create and backfill the canonical audit change feed.

Revision ID: 20260831_0015
Revises: 20260828_0014
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = '20260831_0015'
down_revision = '20260828_0014'
branch_labels = None
depends_on = None


SOURCE_TABLES = (
    'user_activity_periods',
    'area_activity_periods',
    'role_activity_periods',
    'group_activity_periods',
    'user_change_events',
    'access_profile_change_events',
    'approval_policy_change_events',
    'invoice_change_events',
    'approval_step_events',
    'quotation_vote_events',
)


def _schema() -> str | None:
    return op.get_context().config.attributes.get('database_schema')


def _qualified(bind, table: str) -> str:
    preparer = bind.dialect.identifier_preparer
    quoted_table = preparer.quote(table)
    schema = _schema()
    return f'{preparer.quote(schema)}.{quoted_table}' if schema else quoted_table


def _create_feed() -> None:
    schema = _schema()
    json_type = sa.JSON().with_variant(JSONB(), 'postgresql')
    op.create_table(
        'audit_change_feed',
        sa.Column(
            'event_sequence',
            sa.BigInteger().with_variant(sa.Integer(), 'sqlite'),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column('event_id', sa.String(160), nullable=False, unique=True),
        sa.Column(
            'occurred_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column('kind', sa.String(20), nullable=False),
        sa.Column('entity_type', sa.String(40), nullable=False),
        sa.Column('entity_id', sa.String(100), nullable=True),
        sa.Column('event_type', sa.String(80), nullable=False),
        sa.Column('change_type', sa.String(10), nullable=False),
        sa.Column('subject', sa.String(255), nullable=False),
        sa.Column('actor_user_id', sa.Integer(), nullable=True),
        sa.Column('actor_identifier', sa.String(255), nullable=False),
        sa.Column('actor_label', sa.String(255), nullable=False),
        sa.Column('changed_fields', json_type, nullable=False),
        sa.Column('changes', json_type, nullable=False),
        sa.Column('snapshot', json_type, nullable=True),
        sa.Column('event_context', json_type, nullable=False),
        sa.Column('search_text', sa.Text(), nullable=False),
        sa.Column('source_type', sa.String(80), nullable=False),
        sa.Column('source_id', sa.String(120), nullable=False),
        sa.Column('visible', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('schema_version', sa.Integer(), nullable=False, server_default='1'),
        sa.CheckConstraint(
            "change_type IN ('CREATE', 'UPDATE', 'DELETE')",
            name='ck_audit_change_feed_change_type',
        ),
        sa.UniqueConstraint(
            'source_type',
            'source_id',
            name='uq_audit_change_feed_source',
        ),
        schema=schema,
    )
    op.create_index(
        'ix_audit_change_feed_occurred_sequence',
        'audit_change_feed',
        ['occurred_at', 'event_sequence'],
        schema=schema,
    )
    op.create_index(
        'ix_audit_change_feed_kind_occurred_sequence',
        'audit_change_feed',
        ['kind', 'occurred_at', 'event_sequence'],
        schema=schema,
    )
    op.create_index(
        'ix_audit_change_feed_entity_sequence',
        'audit_change_feed',
        ['entity_type', 'entity_id', 'event_sequence'],
        schema=schema,
    )


def _create_backfill_function(bind) -> str:
    if bind.dialect.name != 'postgresql':
        return ''
    preparer = bind.dialect.identifier_preparer
    schema = _schema()
    function_name = preparer.quote('audit_backfill_changes')
    qualified = f'{preparer.quote(schema)}.{function_name}' if schema else function_name
    bind.exec_driver_sql(f'''
        CREATE FUNCTION {qualified}(
            previous_state jsonb,
            current_state jsonb,
            fields jsonb
        ) RETURNS jsonb AS $$
            SELECT COALESCE(
                jsonb_object_agg(
                    field,
                    jsonb_build_object(
                        'before', previous_state -> field,
                        'after', current_state -> field
                    )
                ),
                '{{}}'::jsonb
            )
            FROM jsonb_array_elements_text(COALESCE(fields, '[]'::jsonb)) AS field
            WHERE field !~* '(password|secret|token|hash)'
        $$ LANGUAGE sql IMMUTABLE
    ''')
    return qualified


def _period_event_case(entity_type: str) -> str:
    return f'''
        CASE
          WHEN p.change_type IN ('CREATE', 'BACKFILL') THEN '{entity_type}_CREATED'
          WHEN (p.changes::jsonb -> 'active' ->> 'after') = 'false' THEN '{entity_type}_DEACTIVATED'
          WHEN (p.changes::jsonb -> 'active' ->> 'before') = 'false'
               AND (p.changes::jsonb -> 'active' ->> 'after') = 'true'
            THEN '{entity_type}_REACTIVATED'
          WHEN '{entity_type}' = 'USER' AND p.changed_fields::jsonb ? 'assigned_roles'
            THEN 'USER_ROLES_UPDATED'
          WHEN '{entity_type}' IN ('ROLE', 'GROUP') AND p.changed_fields::jsonb ? 'permission_codes'
            THEN '{entity_type}_PERMISSIONS_UPDATED'
          WHEN '{entity_type}' = 'ROLE' AND p.changed_fields::jsonb ? 'group'
            THEN 'ROLE_GROUP_UPDATED'
          ELSE '{entity_type}_UPDATED'
        END
    '''


def _backfill_period(
    bind,
    *,
    table: str,
    foreign_key: str,
    kind: str,
    entity_type: str,
) -> None:
    feed = _qualified(bind, 'audit_change_feed')
    source = _qualified(bind, table)
    users = _qualified(bind, 'users')
    event_case = _period_event_case(entity_type)
    bind.exec_driver_sql(f'''
        INSERT INTO {feed} (
            event_id, occurred_at, kind, entity_type, entity_id,
            event_type, change_type, subject,
            actor_user_id, actor_identifier, actor_label,
            changed_fields, changes, snapshot, event_context, search_text,
            source_type, source_id, visible, schema_version
        )
        SELECT
            'legacy:{table}:' || p.id::text,
            p.event_at,
            '{kind}',
            '{entity_type}',
            p.{foreign_key}::text,
            {event_case},
            CASE WHEN p.change_type IN ('CREATE', 'BACKFILL') THEN 'CREATE' ELSE 'UPDATE' END,
            COALESCE(p.values::jsonb ->> 'name', p.values::jsonb ->> 'code', '{entity_type}'),
            p.actor_user_id,
            p.actor_identifier,
            COALESCE(
                actor.name,
                CASE
                  WHEN p.actor_identifier LIKE 'SYSTEM:%%' OR p.actor_identifier = 'SYSTEM' THEN 'Sistema'
                  WHEN p.actor_identifier NOT LIKE '%%@%%' THEN p.actor_identifier
                  ELSE 'Sistema'
                END
            ),
            p.changed_fields::jsonb,
            p.changes::jsonb,
            p.values::jsonb,
            jsonb_build_object(
                'legacy_change_type', p.change_type,
                'active_from', p.active_from,
                'active_until', p.active_until
            ),
            concat_ws(' ',
                p.values::text,
                p.changes::text,
                p.actor_identifier,
                {event_case}
            ),
            '{table}',
            p.id::text,
            true,
            1
        FROM {source} AS p
        LEFT JOIN {users} AS actor ON actor.id = p.actor_user_id
        ON CONFLICT (source_type, source_id) DO NOTHING
    ''')


def _backfill_state_events(
    bind,
    *,
    table: str,
    id_column: str,
    entity_id_column: str,
    subject_expression: str,
    kind: str,
    entity_type: str,
    backfill_function: str,
) -> None:
    feed = _qualified(bind, 'audit_change_feed')
    source = _qualified(bind, table)
    users = _qualified(bind, 'users')
    bind.exec_driver_sql(f'''
        INSERT INTO {feed} (
            event_id, occurred_at, kind, entity_type, entity_id,
            event_type, change_type, subject,
            actor_user_id, actor_identifier, actor_label,
            changed_fields, changes, snapshot, event_context, search_text,
            source_type, source_id, visible, schema_version
        )
        SELECT
            'legacy:{table}:' || e.{id_column}::text,
            e.occurred_at,
            '{kind}',
            '{entity_type}',
            e.{entity_id_column}::text,
            e.event_type,
            CASE
              WHEN e.before_state IS NULL AND e.after_state IS NOT NULL THEN 'CREATE'
              WHEN e.after_state IS NULL AND e.before_state IS NOT NULL THEN 'DELETE'
              ELSE 'UPDATE'
            END,
            {subject_expression},
            e.actor_user_id,
            e.actor_email,
            COALESCE(actor.name, 'Sistema'),
            e.changed_fields::jsonb,
            {backfill_function}(
                e.before_state::jsonb,
                e.after_state::jsonb,
                e.changed_fields::jsonb
            ),
            COALESCE(e.after_state::jsonb, e.before_state::jsonb),
            jsonb_build_object('legacy_event_type', e.event_type),
            concat_ws(' ',
                {subject_expression},
                e.actor_email,
                e.event_type,
                e.before_state::text,
                e.after_state::text
            ),
            '{table}',
            e.{id_column}::text,
            true,
            1
        FROM {source} AS e
        LEFT JOIN {users} AS actor ON actor.id = e.actor_user_id
        ON CONFLICT (source_type, source_id) DO NOTHING
    ''')


def _backfill_postgresql(bind) -> None:
    locked_sources = ', '.join(_qualified(bind, table) for table in SOURCE_TABLES)
    bind.exec_driver_sql(f'LOCK TABLE {locked_sources} IN ACCESS EXCLUSIVE MODE')
    backfill_function = _create_backfill_function(bind)
    try:
        for table, foreign_key, kind, entity_type in (
            ('user_activity_periods', 'user_id', 'USER', 'USER'),
            ('area_activity_periods', 'area_id', 'AREA', 'AREA'),
            ('role_activity_periods', 'role_id', 'PERMISSION', 'ROLE'),
            ('group_activity_periods', 'group_id', 'PERMISSION', 'GROUP'),
        ):
            _backfill_period(
                bind,
                table=table,
                foreign_key=foreign_key,
                kind=kind,
                entity_type=entity_type,
            )

        _backfill_state_events(
            bind,
            table='user_change_events',
            id_column='event_id',
            entity_id_column='user_id',
            subject_expression="COALESCE(e.after_state::jsonb ->> 'name', e.before_state::jsonb ->> 'name', e.user_email, 'Usuario')",
            kind='USER',
            entity_type='USER',
            backfill_function=backfill_function,
        )
        _backfill_state_events(
            bind,
            table='access_profile_change_events',
            id_column='event_id',
            entity_id_column='profile_id',
            subject_expression="COALESCE(e.after_state::jsonb ->> 'name', e.before_state::jsonb ->> 'name', e.profile_code)",
            kind='PERMISSION',
            entity_type='PROFILE',
            backfill_function=backfill_function,
        )
        _backfill_state_events(
            bind,
            table='approval_policy_change_events',
            id_column='event_id',
            entity_id_column='policy_id',
            subject_expression='e.policy_name',
            kind='RULE',
            entity_type='RULE',
            backfill_function=backfill_function,
        )

        feed = _qualified(bind, 'audit_change_feed')
        invoices = _qualified(bind, 'invoice_change_events')
        expenses = _qualified(bind, 'expenses')
        users = _qualified(bind, 'users')
        bind.exec_driver_sql(f'''
            INSERT INTO {feed} (
                event_id, occurred_at, kind, entity_type, entity_id,
                event_type, change_type, subject,
                actor_user_id, actor_identifier, actor_label,
                changed_fields, changes, snapshot, event_context, search_text,
                source_type, source_id, visible, schema_version
            )
            SELECT
                'legacy:invoice_change_events:' || e.id::text,
                e.occurred_at,
                'FLOW', 'INVOICE', e.expense_id::text,
                'INVOICE_REPLACED', 'UPDATE', expense.display_id,
                actor.id, e.actor_email, COALESCE(actor.name, 'Sistema'),
                '["attachment_id"]'::jsonb,
                jsonb_build_object(
                    'attachment_id',
                    jsonb_build_object(
                        'before', e.previous_attachment_id,
                        'after', e.new_attachment_id
                    )
                ),
                jsonb_build_object('attachment_id', e.new_attachment_id),
                jsonb_build_object('reason', e.reason),
                concat_ws(' ', expense.display_id, e.actor_email, e.reason, 'INVOICE_REPLACED'),
                'invoice_change_events', e.id::text, true, 1
            FROM {invoices} AS e
            JOIN {expenses} AS expense ON expense.id = e.expense_id
            LEFT JOIN {users} AS actor ON lower(actor.email) = lower(e.actor_email)
            ON CONFLICT (source_type, source_id) DO NOTHING
        ''')

        steps = _qualified(bind, 'approval_step_events')
        bind.exec_driver_sql(f'''
            INSERT INTO {feed} (
                event_id, occurred_at, kind, entity_type, entity_id,
                event_type, change_type, subject,
                actor_user_id, actor_identifier, actor_label,
                changed_fields, changes, snapshot, event_context, search_text,
                source_type, source_id, visible, schema_version
            )
            SELECT
                'legacy:approval_step_events:' || e.event_id,
                e.occurred_at,
                'FLOW', 'APPROVAL_STEP', e.approval_id::text,
                e.event_type, 'UPDATE', e.display_id,
                actor.id, COALESCE(e.actor_email, 'SYSTEM'), COALESCE(actor.name, 'Sistema'),
                '["status"]'::jsonb,
                jsonb_build_object(
                    'status',
                    jsonb_build_object('before', e.previous_status, 'after', e.new_status)
                ),
                jsonb_build_object('status', e.new_status),
                jsonb_build_object(
                    'expense_id', e.expense_id,
                    'request_id', e.request_id,
                    'flow_id', e.flow_id,
                    'step', e.step,
                    'approver_role', e.approver_role,
                    'expense_status', e.expense_status,
                    'comment', e.comment
                ),
                concat_ws(' ', e.display_id, e.event_type, e.actor_email, e.approver_role, e.payload::text),
                'approval_step_events', e.event_id, true, 1
            FROM {steps} AS e
            LEFT JOIN {users} AS actor ON lower(actor.email) = lower(e.actor_email)
            ON CONFLICT (source_type, source_id) DO NOTHING
        ''')

        votes = _qualified(bind, 'quotation_vote_events')
        bind.exec_driver_sql(f'''
            INSERT INTO {feed} (
                event_id, occurred_at, kind, entity_type, entity_id,
                event_type, change_type, subject,
                actor_user_id, actor_identifier, actor_label,
                changed_fields, changes, snapshot, event_context, search_text,
                source_type, source_id, visible, schema_version
            )
            SELECT
                'legacy:quotation_vote_events:' || e.id::text,
                e.occurred_at,
                'FLOW', 'QUOTATION_VOTE', e.expense_id::text || ':' || e.voter_user_id::text,
                CASE WHEN e.previous_option_id IS NULL THEN 'QUOTATION_VOTE_CAST' ELSE 'QUOTATION_VOTE_CHANGED' END,
                CASE WHEN e.previous_option_id IS NULL THEN 'CREATE' ELSE 'UPDATE' END,
                expense.display_id,
                e.voter_user_id, e.voter_email, COALESCE(actor.name, 'Sistema'),
                '["quotation_option_id"]'::jsonb,
                jsonb_build_object(
                    'quotation_option_id',
                    jsonb_build_object('before', e.previous_option_id, 'after', e.selected_option_id)
                ),
                jsonb_build_object('quotation_option_id', e.selected_option_id),
                jsonb_build_object('expense_id', e.expense_id, 'flow_id', e.flow_id, 'voter_role', e.voter_role),
                concat_ws(' ', expense.display_id, e.voter_email, e.voter_role),
                'quotation_vote_events', e.id::text, true, 1
            FROM {votes} AS e
            JOIN {expenses} AS expense ON expense.id = e.expense_id
            LEFT JOIN {users} AS actor ON actor.id = e.voter_user_id
            ON CONFLICT (source_type, source_id) DO NOTHING
        ''')
    finally:
        bind.exec_driver_sql(f'DROP FUNCTION {backfill_function}(jsonb, jsonb, jsonb)')


def _validate_backfill(bind) -> None:
    if bind.dialect.name != 'postgresql':
        return
    feed = _qualified(bind, 'audit_change_feed')
    for table in SOURCE_TABLES:
        source = _qualified(bind, table)
        expected = bind.scalar(sa.text(f'SELECT count(*) FROM {source}')) or 0
        actual = bind.scalar(sa.text(
            f"SELECT count(*) FROM {feed} WHERE source_type = :source_type"
        ), {'source_type': table}) or 0
        if expected != actual:
            raise RuntimeError(
                f'Audit change feed backfill mismatch for {table}: '
                f'expected {expected}, found {actual}'
            )


def _install_guard(bind) -> None:
    feed = _qualified(bind, 'audit_change_feed')
    if bind.dialect.name == 'postgresql':
        preparer = bind.dialect.identifier_preparer
        schema = _schema()
        function = preparer.quote('reject_audit_event_mutation')
        qualified_function = f'{preparer.quote(schema)}.{function}' if schema else function
        bind.exec_driver_sql(f'''
            CREATE TRIGGER audit_change_feed_immutable
            BEFORE UPDATE OR DELETE ON {feed}
            FOR EACH ROW EXECUTE FUNCTION {qualified_function}()
        ''')
        bind.exec_driver_sql(f'''
            CREATE TRIGGER audit_change_feed_no_truncate
            BEFORE TRUNCATE ON {feed}
            FOR EACH STATEMENT EXECUTE FUNCTION {qualified_function}()
        ''')
        return
    bind.exec_driver_sql(f'''
        CREATE TRIGGER audit_change_feed_immutable_update
        BEFORE UPDATE ON {feed}
        BEGIN SELECT RAISE(ABORT, 'audit change feed is append-only'); END
    ''')
    bind.exec_driver_sql(f'''
        CREATE TRIGGER audit_change_feed_immutable_delete
        BEFORE DELETE ON {feed}
        BEGIN SELECT RAISE(ABORT, 'audit change feed is append-only'); END
    ''')


def upgrade() -> None:
    bind = op.get_bind()
    _create_feed()
    if bind.dialect.name == 'postgresql':
        _backfill_postgresql(bind)
    _validate_backfill(bind)
    _install_guard(bind)


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema()
    feed = _qualified(bind, 'audit_change_feed')
    if bind.dialect.name == 'postgresql':
        bind.exec_driver_sql(f'DROP TRIGGER IF EXISTS audit_change_feed_no_truncate ON {feed}')
        bind.exec_driver_sql(f'DROP TRIGGER IF EXISTS audit_change_feed_immutable ON {feed}')
    else:
        bind.exec_driver_sql('DROP TRIGGER IF EXISTS audit_change_feed_immutable_delete')
        bind.exec_driver_sql('DROP TRIGGER IF EXISTS audit_change_feed_immutable_update')
    op.drop_table('audit_change_feed', schema=schema)
