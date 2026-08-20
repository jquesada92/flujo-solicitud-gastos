"""Clean initial schema for fresh installations.

Revision ID: 20260820_0001
Revises: None
Create Date: 2026-08-20

This is the only baseline for the new database lifecycle. It creates the current
application model from scratch inside DATABASE_SCHEMA. It intentionally performs
no legacy table migration, data copy, rename, backfill, or Alembic stamping.
"""

from alembic import context, op
import sqlalchemy as sa


revision = '20260820_0001'
down_revision = None
branch_labels = None
depends_on = None


AUDIT_TABLES = (
    'user_change_events',
    'access_profile_change_events',
    'approval_policy_change_events',
    'invoice_change_events',
    'approval_step_events',
)


def _configured_schema(bind) -> str | None:
    if bind.dialect.name == 'sqlite':
        return None
    schema = context.config.attributes.get('database_schema')
    if not schema:
        raise RuntimeError('DATABASE_SCHEMA must be configured for PostgreSQL migrations')
    return schema


def _table_key(schema: str | None, table: str) -> str:
    return f'{schema}.{table}' if schema else table


def _build_metadata(schema: str | None) -> sa.MetaData:
    metadata = sa.MetaData(schema=schema)

    user_role = sa.Enum('REQUESTER', 'APPROVER', 'VIEWER', 'ADMIN', name='userrole', schema=schema)
    expense_status = sa.Enum(
        'QUOTATION_VOTING',
        'SUBMITTED',
        'PENDING_APPROVAL',
        'APPROVED',
        'REJECTED',
        'CANCELLED',
        'CLOSED',
        'NEEDS_REVISION',
        name='expensestatus',
        schema=schema,
    )
    approval_status = sa.Enum(
        'WAITING',
        'PENDING',
        'APPROVED',
        'REJECTED',
        'REVISION_REQUESTED',
        'EXPIRED',
        name='approvalstatus',
        schema=schema,
    )

    users = sa.Table(
        'users', metadata,
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(150), nullable=False),
        sa.Column('identity_document', sa.String(50), unique=True, nullable=True, index=True),
        sa.Column('analytics_id', sa.String(64), unique=True, nullable=True, index=True),
        sa.Column('phone', sa.String(30), nullable=True),
        sa.Column('first_name', sa.String(70), nullable=True),
        sa.Column('middle_name', sa.String(70), nullable=True),
        sa.Column('last_name', sa.String(70), nullable=True),
        sa.Column('second_last_name', sa.String(70), nullable=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('password_hash', sa.String(512), nullable=False),
        sa.Column('role', user_role, nullable=False),
        sa.Column('title', sa.String(40), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('can_request', sa.Boolean(), nullable=False),
        sa.Column('can_approve', sa.Boolean(), nullable=False),
        sa.Column('can_view', sa.Boolean(), nullable=False),
        sa.Column('can_configure', sa.Boolean(), nullable=False),
        sa.Column('must_change_password', sa.Boolean(), nullable=False),
        sa.Column('session_version', sa.Integer(), nullable=False),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    access_profiles = sa.Table(
        'access_profiles', metadata,
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('code', sa.String(70), unique=True, nullable=False, index=True),
        sa.Column('name', sa.String(120), unique=True, nullable=False),
        sa.Column('can_request', sa.Boolean(), nullable=False),
        sa.Column('can_approve', sa.Boolean(), nullable=False),
        sa.Column('can_view', sa.Boolean(), nullable=False),
        sa.Column('can_configure', sa.Boolean(), nullable=False),
        sa.Column('has_user_limit', sa.Boolean(), nullable=False),
        sa.Column('max_users', sa.Integer(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    user_change_events = sa.Table(
        'user_change_events', metadata,
        sa.Column('event_sequence', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('event_id', sa.String(36), unique=True, nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('event_type', sa.String(40), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False, index=True),
        sa.Column('user_email', sa.String(255), nullable=False),
        sa.Column('actor_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('actor_email', sa.String(255), nullable=False),
        sa.Column('changed_fields', sa.JSON(), nullable=False),
        sa.Column('before_state', sa.JSON(), nullable=True),
        sa.Column('after_state', sa.JSON(), nullable=False),
    )
    sa.Index('ix_user_change_events_user_time', user_change_events.c.user_id, user_change_events.c.occurred_at)

    sa.Table(
        'access_profile_change_events', metadata,
        sa.Column('event_sequence', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('event_id', sa.String(36), unique=True, nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('event_type', sa.String(40), nullable=False),
        sa.Column('profile_id', sa.Integer(), sa.ForeignKey('access_profiles.id', ondelete='RESTRICT'), nullable=False, index=True),
        sa.Column('profile_code', sa.String(70), nullable=False),
        sa.Column('actor_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('actor_email', sa.String(255), nullable=False),
        sa.Column('changed_fields', sa.JSON(), nullable=False),
        sa.Column('before_state', sa.JSON(), nullable=True),
        sa.Column('after_state', sa.JSON(), nullable=False),
    )

    sa.Table(
        'expense_categories', metadata,
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('code', sa.String(80), unique=True, nullable=False, index=True),
        sa.Column('name', sa.String(150), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    sa.Table(
        'expense_subcategories', metadata,
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('category_id', sa.Integer(), sa.ForeignKey('expense_categories.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('code', sa.String(80), nullable=False),
        sa.Column('name', sa.String(150), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
    )

    sa.Table(
        'expense_category_catalog', metadata,
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('code', sa.String(80), unique=True, nullable=False, index=True),
        sa.Column('name', sa.String(150), unique=True, nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    sa.Table(
        'expense_area_categories', metadata,
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('area_id', sa.Integer(), sa.ForeignKey('expense_categories.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('category_id', sa.Integer(), sa.ForeignKey('expense_category_catalog.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.UniqueConstraint('area_id', 'category_id', name='uq_expense_area_category'),
    )

    sa.Table(
        'category_counters', metadata,
        sa.Column('category', sa.String(80), primary_key=True),
        sa.Column('last_value', sa.Integer(), nullable=False),
    )

    sa.Table(
        'expenses', metadata,
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('request_id', sa.String(36), unique=True, nullable=False),
        sa.Column('flow_id', sa.String(36), unique=True, nullable=False),
        sa.Column('display_id', sa.String(40), unique=True, nullable=False),
        sa.Column('revised_from_request_id', sa.String(36), nullable=True, index=True),
        sa.Column('request_type', sa.String(20), nullable=False, index=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('expense_area', sa.String(80), nullable=False, index=True),
        sa.Column('expense_category', sa.String(80), nullable=True),
        sa.Column('urgency', sa.String(20), nullable=False, index=True),
        sa.Column('amount', sa.Numeric(12, 2), nullable=True),
        sa.Column('supplier', sa.String(200), nullable=True),
        sa.Column('item_url', sa.String(2048), nullable=True),
        sa.Column('requested_by', sa.String(255), nullable=False),
        sa.Column('requester_analytics_id', sa.String(64), nullable=True, index=True),
        sa.Column('status', expense_status, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('cancelled_at', sa.DateTime(), nullable=True),
        sa.Column('cancelled_by', sa.String(255), nullable=True),
        sa.Column('cancellation_reason', sa.Text(), nullable=True),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
        sa.Column('closed_by', sa.String(255), nullable=True),
        sa.Column('closure_notes', sa.Text(), nullable=True),
        sa.Column('selected_quotation_id', sa.Integer(), nullable=True),
    )

    sa.Table(
        'quotation_options', metadata,
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('expense_id', sa.Integer(), sa.ForeignKey('expenses.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('option_number', sa.Integer(), nullable=False),
        sa.Column('supplier', sa.String(200), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('item_url', sa.String(2048), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('expense_id', 'option_number', name='uq_quotation_option_number'),
    )

    sa.Table(
        'quotation_votes', metadata,
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('expense_id', sa.Integer(), sa.ForeignKey('expenses.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('quotation_option_id', sa.Integer(), sa.ForeignKey('quotation_options.id'), nullable=False),
        sa.Column('voter_user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('voter_email', sa.String(255), nullable=False),
        sa.Column('voter_role', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('expense_id', 'voter_user_id', name='uq_quotation_vote_voter'),
    )

    sa.Table(
        'quotation_vote_events', metadata,
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('expense_id', sa.Integer(), sa.ForeignKey('expenses.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('flow_id', sa.String(36), nullable=False, index=True),
        sa.Column('voter_user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('voter_email', sa.String(255), nullable=False),
        sa.Column('voter_role', sa.String(100), nullable=False),
        sa.Column('previous_option_id', sa.Integer(), nullable=True),
        sa.Column('selected_option_id', sa.Integer(), nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    sa.Table(
        'quotation_voting_invitations', metadata,
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('expense_id', sa.Integer(), sa.ForeignKey('expenses.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('voter_user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('token', sa.String(100), unique=True, nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('expense_id', 'voter_user_id', name='uq_quotation_invitation_voter'),
    )

    sa.Table(
        'expense_attachments', metadata,
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('expense_id', sa.Integer(), sa.ForeignKey('expenses.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('quotation_option_id', sa.Integer(), sa.ForeignKey('quotation_options.id', ondelete='CASCADE'), nullable=True, index=True),
        sa.Column('original_name', sa.String(255), nullable=False),
        sa.Column('stored_name', sa.String(255), unique=True, nullable=False),
        sa.Column('content_type', sa.String(100), nullable=False),
        sa.Column('size', sa.Integer(), nullable=False),
        sa.Column('document_type', sa.String(40), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    sa.Table(
        'invoice_change_events', metadata,
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('expense_id', sa.Integer(), sa.ForeignKey('expenses.id', ondelete='RESTRICT'), nullable=False, index=True),
        sa.Column('previous_attachment_id', sa.Integer(), sa.ForeignKey('expense_attachments.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('new_attachment_id', sa.Integer(), sa.ForeignKey('expense_attachments.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('actor_email', sa.String(255), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    sa.Table(
        'approval_rules', metadata,
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('expense_type', sa.String(80), nullable=False, index=True),
        sa.Column('min_amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('max_amount', sa.Numeric(12, 2), nullable=True),
        sa.Column('approver_email', sa.String(255), nullable=False),
        sa.Column('approver_role', sa.String(100), nullable=False),
        sa.Column('step', sa.Integer(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
    )

    sa.Table(
        'approval_policies', metadata,
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(120), nullable=False),
        sa.Column('expense_type', sa.String(80), nullable=False, index=True),
        sa.Column('min_amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('max_amount', sa.Numeric(12, 2), nullable=True),
        sa.Column('approval_mode', sa.String(20), nullable=False),
        sa.Column('approver_profile_codes', sa.JSON(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    sa.Table(
        'approval_policy_change_events', metadata,
        sa.Column('event_sequence', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('event_id', sa.String(36), unique=True, nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('event_type', sa.String(40), nullable=False),
        sa.Column('policy_id', sa.Integer(), nullable=False, index=True),
        sa.Column('policy_name', sa.String(120), nullable=False),
        sa.Column('actor_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('actor_email', sa.String(255), nullable=False),
        sa.Column('changed_fields', sa.JSON(), nullable=False),
        sa.Column('before_state', sa.JSON(), nullable=True),
        sa.Column('after_state', sa.JSON(), nullable=True),
    )

    sa.Table(
        'approvals', metadata,
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('expense_id', sa.Integer(), sa.ForeignKey('expenses.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('flow_id', sa.String(36), nullable=False, index=True),
        sa.Column('approver_email', sa.String(255), nullable=False),
        sa.Column('approver_role', sa.String(100), nullable=False),
        sa.Column('step', sa.Integer(), nullable=False),
        sa.Column('approval_mode', sa.String(20), nullable=False),
        sa.Column('token', sa.String(128), unique=True, nullable=False, index=True),
        sa.Column('status', approval_status, nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('decided_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    approval_step_events = sa.Table(
        'approval_step_events', metadata,
        sa.Column('event_sequence', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), primary_key=True, autoincrement=True),
        sa.Column('event_id', sa.String(36), unique=True, nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('expense_id', sa.Integer(), sa.ForeignKey('expenses.id', ondelete='RESTRICT'), nullable=False, index=True),
        sa.Column('approval_id', sa.Integer(), sa.ForeignKey('approvals.id', ondelete='RESTRICT'), nullable=False, index=True),
        sa.Column('request_id', sa.String(36), nullable=False, index=True),
        sa.Column('display_id', sa.String(40), nullable=False),
        sa.Column('flow_id', sa.String(36), nullable=False, index=True),
        sa.Column('step', sa.Integer(), nullable=False),
        sa.Column('approver_email', sa.String(255), nullable=False),
        sa.Column('approver_role', sa.String(100), nullable=False),
        sa.Column('previous_status', sa.String(30), nullable=True),
        sa.Column('new_status', sa.String(30), nullable=False),
        sa.Column('expense_status', sa.String(30), nullable=False),
        sa.Column('actor_email', sa.String(255), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('payload', sa.JSON(), nullable=False),
    )
    sa.Index('ix_approval_step_events_flow_step', approval_step_events.c.flow_id, approval_step_events.c.step, approval_step_events.c.event_sequence)
    sa.Index('ix_approval_step_events_occurred_at', approval_step_events.c.occurred_at)

    permissions = sa.Table(
        'permissions', metadata,
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('code', sa.String(100), unique=True, nullable=False, index=True),
        sa.Column('name', sa.String(150), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    roles = sa.Table(
        'roles', metadata,
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('code', sa.String(100), unique=True, nullable=False, index=True),
        sa.Column('name', sa.String(150), unique=True, nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('system_managed', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    role_permissions = sa.Table(
        'role_permissions', metadata,
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('role_id', sa.Integer(), sa.ForeignKey('roles.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('permission_id', sa.Integer(), sa.ForeignKey('permissions.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.UniqueConstraint('role_id', 'permission_id', name='uq_role_permission'),
    )

    sa.Table(
        'user_groups', metadata,
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('code', sa.String(100), unique=True, nullable=False, index=True),
        sa.Column('name', sa.String(150), unique=True, nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    sa.Table(
        'group_members', metadata,
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('group_id', sa.Integer(), sa.ForeignKey('user_groups.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.UniqueConstraint('group_id', 'user_id', name='uq_group_member'),
    )

    sa.Table(
        'group_roles', metadata,
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('group_id', sa.Integer(), sa.ForeignKey('user_groups.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('role_id', sa.Integer(), sa.ForeignKey('roles.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.UniqueConstraint('group_id', 'role_id', name='uq_group_role'),
    )

    sa.Table(
        'user_role_assignments', metadata,
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('role_id', sa.Integer(), sa.ForeignKey('roles.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.UniqueConstraint('user_id', 'role_id', name='uq_user_role_assignment'),
    )

    sa.Table(
        'user_permissions', metadata,
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('permission_id', sa.Integer(), sa.ForeignKey('permissions.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.UniqueConstraint('user_id', 'permission_id', name='uq_user_permission'),
    )

    sa.Table(
        'positions', metadata,
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('code', sa.String(100), unique=True, nullable=False, index=True),
        sa.Column('name', sa.String(150), unique=True, nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    sa.Table(
        'user_positions', metadata,
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('position_id', sa.Integer(), sa.ForeignKey('positions.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.UniqueConstraint('user_id', 'position_id', name='uq_user_position'),
    )

    sa.Table(
        'position_roles', metadata,
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('position_id', sa.Integer(), sa.ForeignKey('positions.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('role_id', sa.Integer(), sa.ForeignKey('roles.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.UniqueConstraint('position_id', 'role_id', name='uq_position_role'),
    )

    sa.Table(
        'system_accounts', metadata,
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False, index=True),
        sa.Column('account_type', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    expense_closure_delegations = sa.Table(
        'expense_closure_delegations', metadata,
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('expense_id', sa.Integer(), sa.ForeignKey('expenses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('delegate_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('delegated_by_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('delegated_by_email', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_by_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=True),
        sa.Column('revoked_by_email', sa.String(255), nullable=True),
    )
    sa.Index('ix_expense_closure_delegations_expense', expense_closure_delegations.c.expense_id)
    sa.Index('ix_expense_closure_delegations_delegate', expense_closure_delegations.c.delegate_user_id)
    sa.Index(
        'uq_expense_closure_delegation_active',
        expense_closure_delegations.c.expense_id,
        unique=True,
        sqlite_where=expense_closure_delegations.c.revoked_at.is_(None),
        postgresql_where=expense_closure_delegations.c.revoked_at.is_(None),
    )

    # Keep references alive for seed helpers and make the frozen snapshot clear.
    assert users is not None and access_profiles is not None
    assert permissions is not None and roles is not None and role_permissions is not None
    return metadata


def _seed_iam(bind, metadata: sa.MetaData, schema: str | None) -> None:
    permissions = metadata.tables[_table_key(schema, 'permissions')]
    roles = metadata.tables[_table_key(schema, 'roles')]
    role_permissions = metadata.tables[_table_key(schema, 'role_permissions')]

    permission_rows = (
        {
            'code': 'requests:read',
            'name': 'Consultar solicitudes',
            'description': 'Consultar solicitudes y documentos autorizados.',
            'active': True,
        },
        {
            'code': 'requests:create',
            'name': 'Crear solicitudes',
            'description': 'Crear nuevas solicitudes y gestionar solicitudes propias cuando corresponda.',
            'active': True,
        },
        {
            'code': 'requests:approve',
            'name': 'Aprobar solicitudes',
            'description': 'Votar, aprobar, rechazar o enviar solicitudes a revisión cuando corresponda.',
            'active': True,
        },
        {
            'code': 'areas:manage',
            'name': 'Administrar áreas',
            'description': 'Crear, editar, activar/desactivar Áreas y administrar sus Categorías asociadas.',
            'active': True,
        },
        {
            'code': 'config:read',
            'name': 'Consultar configuración',
            'description': 'Consultar Accesos, Áreas, reglas y auditoría sin modificar la configuración.',
            'active': True,
        },
        {
            'code': 'config:manage',
            'name': 'Administración técnica del sistema',
            'description': 'Reservado a system_accounts para administración técnica.',
            'active': True,
        },
        {
            'code': 'requests:close',
            'name': 'Cerrar solicitudes (legacy)',
            'description': 'Registro histórico inactivo; el cierre se autoriza por capacidad de recurso.',
            'active': False,
        },
    )
    bind.execute(sa.insert(permissions), permission_rows)

    role_rows = (
        {
            'code': 'system-administrator',
            'name': 'Administrador del sistema',
            'description': 'Rol técnico protegido; no participa por defecto en el flujo financiero.',
            'active': True,
            'system_managed': True,
        },
        {
            'code': 'area-manager',
            'name': 'Gestor de áreas',
            'description': 'Administra el catálogo de Áreas y sus Categorías asociadas.',
            'active': True,
            'system_managed': False,
        },
        {
            'code': 'configuration-viewer',
            'name': 'Visor de configuración',
            'description': 'Acceso de solo lectura a las pantallas de configuración.',
            'active': True,
            'system_managed': False,
        },
    )
    bind.execute(sa.insert(roles), role_rows)

    permission_ids = dict(bind.execute(sa.select(permissions.c.code, permissions.c.id)).all())
    role_ids = dict(bind.execute(sa.select(roles.c.code, roles.c.id)).all())
    assignments = (
        ('system-administrator', 'config:manage'),
        ('system-administrator', 'config:read'),
        ('system-administrator', 'areas:manage'),
        ('system-administrator', 'requests:read'),
        ('area-manager', 'areas:manage'),
        ('configuration-viewer', 'config:read'),
    )
    bind.execute(
        sa.insert(role_permissions),
        [
            {'role_id': role_ids[role_code], 'permission_id': permission_ids[permission_code]}
            for role_code, permission_code in assignments
        ],
    )


def _install_append_only_guards(bind, schema: str | None) -> None:
    if bind.dialect.name != 'postgresql' or not schema:
        return

    preparer = bind.dialect.identifier_preparer
    q_schema = preparer.quote(schema)
    q_function = preparer.quote('reject_audit_event_mutation')
    bind.exec_driver_sql(f'''
        CREATE OR REPLACE FUNCTION {q_schema}.{q_function}()
        RETURNS trigger AS $$ BEGIN
          RAISE EXCEPTION 'audit event tables are append-only';
        END; $$ LANGUAGE plpgsql
    ''')

    for table in AUDIT_TABLES:
        q_table = preparer.quote(table)
        q_trigger = preparer.quote(f'{table}_immutable')
        bind.exec_driver_sql(f'''
            CREATE TRIGGER {q_trigger}
            BEFORE UPDATE OR DELETE ON {q_schema}.{q_table}
            FOR EACH ROW EXECUTE FUNCTION {q_schema}.{q_function}()
        ''')


def upgrade() -> None:
    bind = op.get_bind()
    schema = _configured_schema(bind)

    existing_tables = set(sa.inspect(bind).get_table_names(schema=schema))
    legacy_tables = existing_tables - {'alembic_version'}
    if legacy_tables:
        names = ', '.join(sorted(legacy_tables))
        raise RuntimeError(
            f'Fresh baseline requires an empty application schema; found existing tables: {names}'
        )

    metadata = _build_metadata(schema)
    metadata.create_all(bind=bind, checkfirst=False)
    _seed_iam(bind, metadata, schema)
    _install_append_only_guards(bind, schema)


def downgrade() -> None:
    bind = op.get_bind()
    schema = _configured_schema(bind)
    metadata = _build_metadata(schema)

    if bind.dialect.name == 'postgresql' and schema:
        preparer = bind.dialect.identifier_preparer
        q_schema = preparer.quote(schema)
        q_function = preparer.quote('reject_audit_event_mutation')
        metadata.drop_all(bind=bind, checkfirst=True)
        bind.exec_driver_sql(f'DROP FUNCTION IF EXISTS {q_schema}.{q_function}()')
    else:
        metadata.drop_all(bind=bind, checkfirst=True)
