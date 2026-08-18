"""Application schema baseline for existing and clean databases.

Revision ID: 20260817_0000
Revises: None
Create Date: 2026-08-17

Every table definition is frozen in this migration. Existing production tables
are detected and left in place; a clean database receives the same property-free
baseline before IAM revisions are applied.
"""

from alembic import op
import sqlalchemy as sa

revision = '20260817_0000'
down_revision = None
branch_labels = None
depends_on = None

USER_ROLE = sa.Enum('REQUESTER', 'APPROVER', 'VIEWER', 'ADMIN', name='userrole')
EXPENSE_STATUS = sa.Enum(
    'QUOTATION_VOTING', 'SUBMITTED', 'PENDING_APPROVAL', 'APPROVED',
    'REJECTED', 'CANCELLED', 'CLOSED', 'NEEDS_REVISION',
    name='expensestatus',
)
APPROVAL_STATUS = sa.Enum(
    'WAITING', 'PENDING', 'APPROVED', 'REJECTED', 'REVISION_REQUESTED', 'EXPIRED',
    name='approvalstatus',
)


def _has(table: str) -> bool:
    return table in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if not _has('users'):
        op.create_table(
            'users',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('name', sa.String(150), nullable=False),
            sa.Column('identity_document', sa.String(50), nullable=True),
            sa.Column('analytics_id', sa.String(64), nullable=True),
            sa.Column('phone', sa.String(30), nullable=True),
            sa.Column('first_name', sa.String(70), nullable=True),
            sa.Column('middle_name', sa.String(70), nullable=True),
            sa.Column('last_name', sa.String(70), nullable=True),
            sa.Column('second_last_name', sa.String(70), nullable=True),
            sa.Column('email', sa.String(255), nullable=False),
            sa.Column('password_hash', sa.String(512), nullable=False),
            sa.Column('role', USER_ROLE, nullable=False),
            sa.Column('title', sa.String(40), nullable=False, server_default='SIN_ASIGNAR'),
            sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('can_request', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('can_approve', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('can_view', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('can_configure', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('must_change_password', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('session_version', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint('identity_document', name='uq_users_identity_document'),
            sa.UniqueConstraint('analytics_id', name='uq_users_analytics_id'),
            sa.UniqueConstraint('email', name='uq_users_email'),
        )
        op.create_index('ix_users_identity_document', 'users', ['identity_document'])
        op.create_index('ix_users_analytics_id', 'users', ['analytics_id'])
        op.create_index('ix_users_email', 'users', ['email'])

    if not _has('access_profiles'):
        op.create_table(
            'access_profiles',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('code', sa.String(70), nullable=False),
            sa.Column('name', sa.String(120), nullable=False),
            sa.Column('can_request', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('can_approve', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('can_view', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('can_configure', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('has_user_limit', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('max_users', sa.Integer(), nullable=True),
            sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint('code', name='uq_access_profiles_code'),
            sa.UniqueConstraint('name', name='uq_access_profiles_name'),
        )
        op.create_index('ix_access_profiles_code', 'access_profiles', ['code'])

    if not _has('user_change_events'):
        op.create_table(
            'user_change_events',
            sa.Column('event_sequence', sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column('event_id', sa.String(36), nullable=False),
            sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column('event_type', sa.String(40), nullable=False),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
            sa.Column('user_email', sa.String(255), nullable=False),
            sa.Column('actor_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
            sa.Column('actor_email', sa.String(255), nullable=False),
            sa.Column('changed_fields', sa.JSON(), nullable=False),
            sa.Column('before_state', sa.JSON(), nullable=True),
            sa.Column('after_state', sa.JSON(), nullable=False),
            sa.UniqueConstraint('event_id', name='uq_user_change_events_event_id'),
        )
        op.create_index('ix_user_change_events_user_time', 'user_change_events', ['user_id', 'occurred_at'])

    if not _has('access_profile_change_events'):
        op.create_table(
            'access_profile_change_events',
            sa.Column('event_sequence', sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column('event_id', sa.String(36), nullable=False),
            sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column('event_type', sa.String(40), nullable=False),
            sa.Column('profile_id', sa.Integer(), sa.ForeignKey('access_profiles.id', ondelete='RESTRICT'), nullable=False),
            sa.Column('profile_code', sa.String(70), nullable=False),
            sa.Column('actor_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
            sa.Column('actor_email', sa.String(255), nullable=False),
            sa.Column('changed_fields', sa.JSON(), nullable=False),
            sa.Column('before_state', sa.JSON(), nullable=True),
            sa.Column('after_state', sa.JSON(), nullable=False),
            sa.UniqueConstraint('event_id', name='uq_access_profile_change_event_id'),
        )
        op.create_index('ix_access_profile_change_events_profile_id', 'access_profile_change_events', ['profile_id'])

    if not _has('expense_categories'):
        op.create_table(
            'expense_categories',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('code', sa.String(80), nullable=False),
            sa.Column('name', sa.String(150), nullable=False),
            sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint('code', name='uq_expense_categories_code'),
        )
        op.create_index('ix_expense_categories_code', 'expense_categories', ['code'])

    if not _has('expense_subcategories'):
        op.create_table(
            'expense_subcategories',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('category_id', sa.Integer(), sa.ForeignKey('expense_categories.id', ondelete='CASCADE'), nullable=False),
            sa.Column('code', sa.String(80), nullable=False),
            sa.Column('name', sa.String(150), nullable=False),
            sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
        )
        op.create_index('ix_expense_subcategories_category_id', 'expense_subcategories', ['category_id'])

    if not _has('expense_category_catalog'):
        op.create_table(
            'expense_category_catalog',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('code', sa.String(80), nullable=False),
            sa.Column('name', sa.String(150), nullable=False),
            sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint('code', name='uq_expense_category_catalog_code'),
            sa.UniqueConstraint('name', name='uq_expense_category_catalog_name'),
        )
        op.create_index('ix_expense_category_catalog_code', 'expense_category_catalog', ['code'])

    if not _has('expense_area_categories'):
        op.create_table(
            'expense_area_categories',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('area_id', sa.Integer(), sa.ForeignKey('expense_categories.id', ondelete='CASCADE'), nullable=False),
            sa.Column('category_id', sa.Integer(), sa.ForeignKey('expense_category_catalog.id', ondelete='CASCADE'), nullable=False),
            sa.UniqueConstraint('area_id', 'category_id', name='uq_expense_area_category'),
        )
        op.create_index('ix_expense_area_categories_area_id', 'expense_area_categories', ['area_id'])
        op.create_index('ix_expense_area_categories_category_id', 'expense_area_categories', ['category_id'])

    if not _has('category_counters'):
        op.create_table(
            'category_counters',
            sa.Column('category', sa.String(80), primary_key=True),
            sa.Column('last_value', sa.Integer(), nullable=False, server_default='0'),
        )

    if not _has('expenses'):
        op.create_table(
            'expenses',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('request_id', sa.String(36), nullable=False),
            sa.Column('flow_id', sa.String(36), nullable=False),
            sa.Column('display_id', sa.String(40), nullable=False),
            sa.Column('revised_from_request_id', sa.String(36), nullable=True),
            sa.Column('request_type', sa.String(20), nullable=False, server_default='SIMPLE'),
            sa.Column('title', sa.String(200), nullable=False),
            sa.Column('description', sa.Text(), nullable=False),
            sa.Column('expense_type', sa.String(80), nullable=False),
            sa.Column('expense_subcategory', sa.String(80), nullable=True),
            sa.Column('urgency', sa.String(20), nullable=False, server_default='NORMAL'),
            sa.Column('amount', sa.Numeric(12, 2), nullable=True),
            sa.Column('supplier', sa.String(200), nullable=True),
            sa.Column('item_url', sa.String(2048), nullable=True),
            sa.Column('requested_by', sa.String(255), nullable=False),
            sa.Column('requester_analytics_id', sa.String(64), nullable=True),
            sa.Column('status', EXPENSE_STATUS, nullable=False, server_default='SUBMITTED'),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('cancelled_at', sa.DateTime(), nullable=True),
            sa.Column('cancelled_by', sa.String(255), nullable=True),
            sa.Column('cancellation_reason', sa.Text(), nullable=True),
            sa.Column('closed_at', sa.DateTime(), nullable=True),
            sa.Column('closed_by', sa.String(255), nullable=True),
            sa.Column('closure_notes', sa.Text(), nullable=True),
            sa.Column('selected_quotation_id', sa.Integer(), nullable=True),
            sa.UniqueConstraint('request_id', name='uq_expenses_request_id'),
            sa.UniqueConstraint('flow_id', name='uq_expenses_flow_id'),
            sa.UniqueConstraint('display_id', name='uq_expenses_display_id'),
        )
        for name, cols in (
            ('ix_expenses_revised_from', ['revised_from_request_id']),
            ('ix_expenses_request_type', ['request_type']),
            ('ix_expenses_expense_type', ['expense_type']),
            ('ix_expenses_urgency', ['urgency']),
            ('ix_expenses_requester_analytics_id', ['requester_analytics_id']),
        ):
            op.create_index(name, 'expenses', cols)

    if not _has('quotation_options'):
        op.create_table(
            'quotation_options',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('expense_id', sa.Integer(), sa.ForeignKey('expenses.id', ondelete='CASCADE'), nullable=False),
            sa.Column('option_number', sa.Integer(), nullable=False),
            sa.Column('supplier', sa.String(200), nullable=False),
            sa.Column('amount', sa.Numeric(12, 2), nullable=False),
            sa.Column('item_url', sa.String(2048), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint('expense_id', 'option_number', name='uq_quotation_option_number'),
        )
        op.create_index('ix_quotation_options_expense_id', 'quotation_options', ['expense_id'])

    if not _has('quotation_votes'):
        op.create_table(
            'quotation_votes',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('expense_id', sa.Integer(), sa.ForeignKey('expenses.id', ondelete='CASCADE'), nullable=False),
            sa.Column('quotation_option_id', sa.Integer(), sa.ForeignKey('quotation_options.id'), nullable=False),
            sa.Column('voter_user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('voter_email', sa.String(255), nullable=False),
            sa.Column('voter_role', sa.String(100), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint('expense_id', 'voter_user_id', name='uq_quotation_vote_voter'),
        )
        op.create_index('ix_quotation_votes_expense_id', 'quotation_votes', ['expense_id'])

    if not _has('quotation_vote_events'):
        op.create_table(
            'quotation_vote_events',
            sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column('expense_id', sa.Integer(), sa.ForeignKey('expenses.id', ondelete='CASCADE'), nullable=False),
            sa.Column('flow_id', sa.String(36), nullable=False),
            sa.Column('voter_user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('voter_email', sa.String(255), nullable=False),
            sa.Column('voter_role', sa.String(100), nullable=False),
            sa.Column('previous_option_id', sa.Integer(), nullable=True),
            sa.Column('selected_option_id', sa.Integer(), nullable=False),
            sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index('ix_quotation_vote_events_expense_id', 'quotation_vote_events', ['expense_id'])
        op.create_index('ix_quotation_vote_events_flow_id', 'quotation_vote_events', ['flow_id'])

    if not _has('quotation_voting_invitations'):
        op.create_table(
            'quotation_voting_invitations',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('expense_id', sa.Integer(), sa.ForeignKey('expenses.id', ondelete='CASCADE'), nullable=False),
            sa.Column('voter_user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('token', sa.String(100), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint('expense_id', 'voter_user_id', name='uq_quotation_invitation_voter'),
            sa.UniqueConstraint('token', name='uq_quotation_voting_invitations_token'),
        )
        op.create_index('ix_quotation_voting_invitations_expense_id', 'quotation_voting_invitations', ['expense_id'])
        op.create_index('ix_quotation_voting_invitations_token', 'quotation_voting_invitations', ['token'])

    if not _has('expense_attachments'):
        op.create_table(
            'expense_attachments',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('expense_id', sa.Integer(), sa.ForeignKey('expenses.id', ondelete='CASCADE'), nullable=False),
            sa.Column('quotation_option_id', sa.Integer(), sa.ForeignKey('quotation_options.id', ondelete='CASCADE'), nullable=True),
            sa.Column('original_name', sa.String(255), nullable=False),
            sa.Column('stored_name', sa.String(255), nullable=False),
            sa.Column('content_type', sa.String(100), nullable=False),
            sa.Column('size', sa.Integer(), nullable=False),
            sa.Column('document_type', sa.String(40), nullable=False, server_default='QUOTATION'),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint('stored_name', name='uq_expense_attachments_stored_name'),
        )
        op.create_index('ix_expense_attachments_expense_id', 'expense_attachments', ['expense_id'])
        op.create_index('ix_expense_attachments_quotation_option_id', 'expense_attachments', ['quotation_option_id'])

    if not _has('invoice_change_events'):
        op.create_table(
            'invoice_change_events',
            sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column('expense_id', sa.Integer(), sa.ForeignKey('expenses.id', ondelete='RESTRICT'), nullable=False),
            sa.Column('previous_attachment_id', sa.Integer(), sa.ForeignKey('expense_attachments.id', ondelete='RESTRICT'), nullable=False),
            sa.Column('new_attachment_id', sa.Integer(), sa.ForeignKey('expense_attachments.id', ondelete='RESTRICT'), nullable=False),
            sa.Column('actor_email', sa.String(255), nullable=False),
            sa.Column('reason', sa.Text(), nullable=False),
            sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index('ix_invoice_change_events_expense_id', 'invoice_change_events', ['expense_id'])

    if not _has('approval_rules'):
        op.create_table(
            'approval_rules',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('expense_type', sa.String(80), nullable=False),
            sa.Column('min_amount', sa.Numeric(12, 2), nullable=False, server_default='0'),
            sa.Column('max_amount', sa.Numeric(12, 2), nullable=True),
            sa.Column('approver_email', sa.String(255), nullable=False),
            sa.Column('approver_role', sa.String(100), nullable=False),
            sa.Column('step', sa.Integer(), nullable=False),
            sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
        )
        op.create_index('ix_approval_rules_expense_type', 'approval_rules', ['expense_type'])

    if not _has('approval_policies'):
        op.create_table(
            'approval_policies',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('name', sa.String(120), nullable=False),
            sa.Column('expense_type', sa.String(80), nullable=False, server_default='ALL'),
            sa.Column('min_amount', sa.Numeric(12, 2), nullable=False, server_default='0'),
            sa.Column('max_amount', sa.Numeric(12, 2), nullable=True),
            sa.Column('approval_mode', sa.String(20), nullable=False, server_default='ANY'),
            sa.Column('approver_profile_codes', sa.JSON(), nullable=False, server_default='[]'),
            sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index('ix_approval_policies_expense_type', 'approval_policies', ['expense_type'])

    if not _has('approval_policy_change_events'):
        op.create_table(
            'approval_policy_change_events',
            sa.Column('event_sequence', sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column('event_id', sa.String(36), nullable=False),
            sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column('event_type', sa.String(40), nullable=False),
            sa.Column('policy_id', sa.Integer(), nullable=False),
            sa.Column('policy_name', sa.String(120), nullable=False),
            sa.Column('actor_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
            sa.Column('actor_email', sa.String(255), nullable=False),
            sa.Column('changed_fields', sa.JSON(), nullable=False),
            sa.Column('before_state', sa.JSON(), nullable=True),
            sa.Column('after_state', sa.JSON(), nullable=True),
            sa.UniqueConstraint('event_id', name='uq_approval_policy_change_events_event_id'),
        )
        op.create_index('ix_approval_policy_change_events_policy_id', 'approval_policy_change_events', ['policy_id'])

    if not _has('approvals'):
        op.create_table(
            'approvals',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('expense_id', sa.Integer(), sa.ForeignKey('expenses.id', ondelete='CASCADE'), nullable=False),
            sa.Column('flow_id', sa.String(36), nullable=False),
            sa.Column('approver_email', sa.String(255), nullable=False),
            sa.Column('approver_role', sa.String(100), nullable=False),
            sa.Column('step', sa.Integer(), nullable=False),
            sa.Column('approval_mode', sa.String(20), nullable=False, server_default='SEQUENTIAL'),
            sa.Column('token', sa.String(128), nullable=False),
            sa.Column('status', APPROVAL_STATUS, nullable=False, server_default='WAITING'),
            sa.Column('comment', sa.Text(), nullable=True),
            sa.Column('decided_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint('token', name='uq_approvals_token'),
        )
        op.create_index('ix_approvals_expense_id', 'approvals', ['expense_id'])
        op.create_index('ix_approvals_flow_id', 'approvals', ['flow_id'])
        op.create_index('ix_approvals_token', 'approvals', ['token'])

    if not _has('approval_step_events'):
        op.create_table(
            'approval_step_events',
            sa.Column('event_sequence', sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column('event_id', sa.String(36), nullable=False),
            sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column('event_type', sa.String(50), nullable=False),
            sa.Column('expense_id', sa.Integer(), sa.ForeignKey('expenses.id', ondelete='RESTRICT'), nullable=False),
            sa.Column('approval_id', sa.Integer(), sa.ForeignKey('approvals.id', ondelete='RESTRICT'), nullable=False),
            sa.Column('request_id', sa.String(36), nullable=False),
            sa.Column('display_id', sa.String(40), nullable=False),
            sa.Column('flow_id', sa.String(36), nullable=False),
            sa.Column('step', sa.Integer(), nullable=False),
            sa.Column('approver_email', sa.String(255), nullable=False),
            sa.Column('approver_role', sa.String(100), nullable=False),
            sa.Column('previous_status', sa.String(30), nullable=True),
            sa.Column('new_status', sa.String(30), nullable=False),
            sa.Column('expense_status', sa.String(30), nullable=False),
            sa.Column('actor_email', sa.String(255), nullable=True),
            sa.Column('comment', sa.Text(), nullable=True),
            sa.Column('payload', sa.JSON(), nullable=False),
            sa.UniqueConstraint('event_id', name='uq_approval_step_events_event_id'),
        )
        op.create_index('ix_approval_step_events_expense_id', 'approval_step_events', ['expense_id'])
        op.create_index('ix_approval_step_events_approval_id', 'approval_step_events', ['approval_id'])
        op.create_index('ix_approval_step_events_request_id', 'approval_step_events', ['request_id'])
        op.create_index('ix_approval_step_events_flow_id', 'approval_step_events', ['flow_id'])
        op.create_index('ix_approval_step_events_flow_step', 'approval_step_events', ['flow_id', 'step', 'event_sequence'])
        op.create_index('ix_approval_step_events_occurred_at', 'approval_step_events', ['occurred_at'])

    # Preserve append-only protections previously created by startup compatibility code.
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        bind.execute(sa.text('''
            CREATE OR REPLACE FUNCTION reject_audit_event_mutation()
            RETURNS trigger AS $$ BEGIN
              RAISE EXCEPTION 'audit event tables are append-only';
            END; $$ LANGUAGE plpgsql
        '''))
        for table in (
            'user_change_events',
            'access_profile_change_events',
            'approval_policy_change_events',
            'invoice_change_events',
            'approval_step_events',
        ):
            bind.execute(sa.text(f'DROP TRIGGER IF EXISTS {table}_immutable ON {table}'))
            bind.execute(sa.text(f'''
                CREATE TRIGGER {table}_immutable
                BEFORE UPDATE OR DELETE ON {table}
                FOR EACH ROW EXECUTE FUNCTION reject_audit_event_mutation()
            '''))


def downgrade() -> None:
    # This baseline may be applied to a pre-existing production schema. Dropping
    # it during downgrade could destroy data that Alembic did not create.
    # Recovery for the baseline is therefore snapshot/restore, not table drops.
    pass
