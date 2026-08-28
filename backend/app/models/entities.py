import enum
import secrets
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, BigInteger, Boolean, CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from app.core.database import Base


class ExpenseStatus(str, enum.Enum):
    QUOTATION_VOTING = 'QUOTATION_VOTING'
    SUBMITTED = 'SUBMITTED'
    PENDING_APPROVAL = 'PENDING_APPROVAL'
    APPROVED = 'APPROVED'
    REJECTED = 'REJECTED'
    CANCELLED = 'CANCELLED'
    CLOSED = 'CLOSED'
    NEEDS_REVISION = 'NEEDS_REVISION'


class ApprovalStatus(str, enum.Enum):
    WAITING = 'WAITING'
    PENDING = 'PENDING'
    APPROVED = 'APPROVED'
    REJECTED = 'REJECTED'
    REVISION_REQUESTED = 'REVISION_REQUESTED'
    EXPIRED = 'EXPIRED'


class UserRole(str, enum.Enum):
    REQUESTER = 'REQUESTER'
    APPROVER = 'APPROVER'
    VIEWER = 'VIEWER'
    ADMIN = 'ADMIN'


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    identity_document: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True, index=True)
    analytics_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(70), nullable=True)
    middle_name: Mapped[str | None] = mapped_column(String(70), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(70), nullable=True)
    second_last_name: Mapped[str | None] = mapped_column(String(70), nullable=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, inherit_schema=True), nullable=False)
    title: Mapped[str] = mapped_column(String(40), nullable=False, default='SIN_ASIGNAR')
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    can_request: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    can_approve: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    can_view: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    can_configure: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    session_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    password_reset_version: Mapped[int] = mapped_column(Integer, default=0, server_default='0', nullable=False)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    @property
    def full_name(self) -> str:
        parts = (self.first_name, self.middle_name, self.last_name, self.second_last_name)
        return ' '.join(part.strip() for part in parts if part and part.strip()) or self.name


class UserChangeEvent(Base):
    """Immutable audit trail for user access and permission changes."""

    __tablename__ = 'user_change_events'
    __table_args__ = (
        Index('ix_user_change_events_user_time', 'user_id', 'occurred_at'),
    )

    event_sequence: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, 'sqlite'),
        primary_key=True,
        autoincrement=True,
    )
    event_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), nullable=False, index=True)
    user_email: Mapped[str] = mapped_column(String(255), nullable=False)
    actor_user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    actor_email: Mapped[str] = mapped_column(String(255), nullable=False)
    changed_fields: Mapped[list] = mapped_column(JSON, nullable=False)
    before_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after_state: Mapped[dict] = mapped_column(JSON, nullable=False)


class AccessProfile(Base):
    __tablename__ = 'access_profiles'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(70), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    can_request: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    can_approve: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    can_view: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    can_configure: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_user_limit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    max_users: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AccessProfileChangeEvent(Base):
    __tablename__ = 'access_profile_change_events'

    event_sequence: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    profile_id: Mapped[int] = mapped_column(ForeignKey('access_profiles.id', ondelete='RESTRICT'), nullable=False, index=True)
    profile_code: Mapped[str] = mapped_column(String(70), nullable=False)
    actor_user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    actor_email: Mapped[str] = mapped_column(String(255), nullable=False)
    changed_fields: Mapped[list] = mapped_column(JSON, nullable=False)
    before_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after_state: Mapped[dict] = mapped_column(JSON, nullable=False)


class Expense(Base):
    __tablename__ = 'expenses'
    __table_args__ = (
        CheckConstraint(
            'minimum_votes_required IS NULL OR minimum_votes_required >= 1',
            name='ck_expenses_minimum_votes_required_positive',
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    flow_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    display_id: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    revised_from_request_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    request_type: Mapped[str] = mapped_column(String(20), nullable=False, default='SIMPLE', index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    expense_area: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    expense_category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    urgency: Mapped[str] = mapped_column(String(20), nullable=False, default='NORMAL', index=True)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    supplier: Mapped[str | None] = mapped_column(String(200), nullable=True)
    item_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    requested_by: Mapped[str] = mapped_column(String(255), nullable=False)
    requester_analytics_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[ExpenseStatus] = mapped_column(
        Enum(ExpenseStatus, inherit_schema=True),
        default=ExpenseStatus.SUBMITTED,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancelled_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    closed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    closure_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    selected_quotation_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Policy fields are immutable snapshots of the rule used to open the round.
    # approval_policy_id intentionally has no FK: deleting/editing a policy must
    # not change the behavior or audit evidence of an already-open request.
    approval_policy_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    approval_policy_mode: Mapped[str | None] = mapped_column(String(20), nullable=True)
    policy_evaluation_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    minimum_votes_required: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Transitional aliases keep older internal callers working while the
    # canonical ORM and physical database columns remain expense_area/category.
    expense_type = synonym('expense_area')
    expense_subcategory = synonym('expense_category')

    approvals = relationship('Approval', back_populates='expense', cascade='all, delete-orphan', order_by='Approval.step')
    attachments = relationship('ExpenseAttachment', back_populates='expense', cascade='all, delete-orphan')
    quotation_options = relationship('QuotationOption', back_populates='expense', cascade='all, delete-orphan', order_by='QuotationOption.option_number')
    quotation_votes = relationship('QuotationVote', back_populates='expense', cascade='all, delete-orphan')


class DirectExpense(Base):
    """Final expense record for an applicable NO_APPROVAL amount band.

    This is deliberately independent from Expense and every workflow table.
    The policy identifier is historical evidence rather than a destructive FK,
    matching the immutable policy snapshot convention used by open requests.
    """

    __tablename__ = 'direct_expenses'
    __table_args__ = (
        CheckConstraint('amount > 0', name='ck_direct_expenses_amount_positive'),
        CheckConstraint('invoice_size > 0', name='ck_direct_expenses_invoice_size_positive'),
        Index(
            'ix_direct_expenses_requester_created',
            'requester_user_id',
            'created_at',
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    record_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        nullable=False,
        default=lambda: str(uuid.uuid4()),
    )
    display_id: Mapped[str] = mapped_column(
        String(40),
        unique=True,
        nullable=False,
        default=lambda: f'GD-{uuid.uuid4()}',
    )
    expense_area: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    supplier: Mapped[str] = mapped_column(String(200), nullable=False)
    item_description: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    requester_user_id: Mapped[int] = mapped_column(
        ForeignKey('users.id', ondelete='RESTRICT'),
        nullable=False,
    )
    requester_analytics_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    requester_email: Mapped[str] = mapped_column(String(255), nullable=False)
    invoice_original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    invoice_stored_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    invoice_content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    invoice_size: Mapped[int] = mapped_column(Integer, nullable=False)
    approval_policy_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class QuotationOption(Base):
    __tablename__ = 'quotation_options'
    __table_args__ = (UniqueConstraint('expense_id', 'option_number', name='uq_quotation_option_number'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    expense_id: Mapped[int] = mapped_column(ForeignKey('expenses.id', ondelete='CASCADE'), nullable=False, index=True)
    option_number: Mapped[int] = mapped_column(Integer, nullable=False)
    supplier: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    item_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expense = relationship('Expense', back_populates='quotation_options')


class QuotationVote(Base):
    __tablename__ = 'quotation_votes'
    __table_args__ = (UniqueConstraint('expense_id', 'voter_user_id', name='uq_quotation_vote_voter'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    expense_id: Mapped[int] = mapped_column(ForeignKey('expenses.id', ondelete='CASCADE'), nullable=False, index=True)
    quotation_option_id: Mapped[int] = mapped_column(ForeignKey('quotation_options.id'), nullable=False)
    voter_user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    voter_email: Mapped[str] = mapped_column(String(255), nullable=False)
    voter_role: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    expense = relationship('Expense', back_populates='quotation_votes')


class QuotationVoteEvent(Base):
    __tablename__ = 'quotation_vote_events'

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, 'sqlite'),
        primary_key=True,
        autoincrement=True,
    )
    expense_id: Mapped[int] = mapped_column(ForeignKey('expenses.id', ondelete='CASCADE'), nullable=False, index=True)
    flow_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    voter_user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    voter_email: Mapped[str] = mapped_column(String(255), nullable=False)
    voter_role: Mapped[str] = mapped_column(String(100), nullable=False)
    previous_option_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    selected_option_id: Mapped[int] = mapped_column(Integer, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class QuotationVotingInvitation(Base):
    __tablename__ = 'quotation_voting_invitations'
    __table_args__ = (UniqueConstraint('expense_id', 'voter_user_id', name='uq_quotation_invitation_voter'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    expense_id: Mapped[int] = mapped_column(ForeignKey('expenses.id', ondelete='CASCADE'), nullable=False, index=True)
    voter_user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    token: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True, default=lambda: secrets.token_urlsafe(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AreaCounter(Base):
    """Compatibility mapping for the legacy category_counters table."""

    __tablename__ = 'category_counters'

    area_key: Mapped[str] = mapped_column('category', String(80), primary_key=True)
    last_value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class ExpenseArea(Base):
    """Application-level Area mapped to the legacy expense_categories table."""

    __tablename__ = 'expense_categories'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    subcategories = relationship('ExpenseSubcategory', back_populates='area', cascade='all, delete-orphan', order_by='ExpenseSubcategory.name')


class ExpenseSubcategory(Base):
    __tablename__ = 'expense_subcategories'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    area_id: Mapped[int] = mapped_column('category_id', ForeignKey('expense_categories.id', ondelete='CASCADE'), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    area = relationship('ExpenseArea', back_populates='subcategories')


class ExpenseAttachment(Base):
    __tablename__ = 'expense_attachments'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    expense_id: Mapped[int] = mapped_column(ForeignKey('expenses.id', ondelete='CASCADE'), nullable=False, index=True)
    quotation_option_id: Mapped[int | None] = mapped_column(ForeignKey('quotation_options.id', ondelete='CASCADE'), nullable=True, index=True)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    document_type: Mapped[str] = mapped_column(String(40), nullable=False, default='QUOTATION')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    expense = relationship('Expense', back_populates='attachments')


class InvoiceChangeEvent(Base):
    __tablename__ = 'invoice_change_events'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    expense_id: Mapped[int] = mapped_column(ForeignKey('expenses.id', ondelete='RESTRICT'), nullable=False, index=True)
    previous_attachment_id: Mapped[int] = mapped_column(ForeignKey('expense_attachments.id', ondelete='RESTRICT'), nullable=False)
    new_attachment_id: Mapped[int] = mapped_column(ForeignKey('expense_attachments.id', ondelete='RESTRICT'), nullable=False)
    actor_email: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ApprovalRule(Base):
    __tablename__ = 'approval_rules'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    expense_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    min_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    max_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    approver_email: Mapped[str] = mapped_column(String(255), nullable=False)
    approver_role: Mapped[str] = mapped_column(String(100), nullable=False)
    step: Mapped[int] = mapped_column(Integer, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ApprovalPolicy(Base):
    """Configurable amount band and the quorum required for its approvers."""

    __tablename__ = 'approval_policies'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    expense_type: Mapped[str] = mapped_column(String(80), nullable=False, default='ALL', index=True)
    min_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    max_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    approval_mode: Mapped[str] = mapped_column(String(20), nullable=False, default='ANY')
    approver_profile_codes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    approver_role_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    approver_group_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class ApprovalPolicyChangeEvent(Base):
    """Append-only history for approval-rule configuration changes."""

    __tablename__ = 'approval_policy_change_events'

    event_sequence: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, 'sqlite'),
        primary_key=True,
        autoincrement=True,
    )
    event_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    policy_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    policy_name: Mapped[str] = mapped_column(String(120), nullable=False)
    actor_user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    actor_email: Mapped[str] = mapped_column(String(255), nullable=False)
    changed_fields: Mapped[list] = mapped_column(JSON, nullable=False)
    before_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class Approval(Base):
    __tablename__ = 'approvals'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    expense_id: Mapped[int] = mapped_column(ForeignKey('expenses.id', ondelete='CASCADE'), nullable=False, index=True)
    flow_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    approver_email: Mapped[str] = mapped_column(String(255), nullable=False)
    approver_role: Mapped[str] = mapped_column(String(100), nullable=False)
    step: Mapped[int] = mapped_column(Integer, nullable=False)
    approval_mode: Mapped[str] = mapped_column(String(20), nullable=False, default='SEQUENTIAL')
    token: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus, inherit_schema=True),
        default=ApprovalStatus.WAITING,
        nullable=False,
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    expense = relationship('Expense', back_populates='approvals')


class ApprovalStepEvent(Base):
    """Append-only approval history prepared for future CDC ingestion."""

    __tablename__ = 'approval_step_events'
    __table_args__ = (
        Index('ix_approval_step_events_flow_step', 'flow_id', 'step', 'event_sequence'),
        Index('ix_approval_step_events_occurred_at', 'occurred_at'),
    )

    event_sequence: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, 'sqlite'),
        primary_key=True,
        autoincrement=True,
    )
    event_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    expense_id: Mapped[int] = mapped_column(ForeignKey('expenses.id', ondelete='RESTRICT'), nullable=False, index=True)
    approval_id: Mapped[int] = mapped_column(ForeignKey('approvals.id', ondelete='RESTRICT'), nullable=False, index=True)
    request_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    display_id: Mapped[str] = mapped_column(String(40), nullable=False)
    flow_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    step: Mapped[int] = mapped_column(Integer, nullable=False)
    approver_email: Mapped[str] = mapped_column(String(255), nullable=False)
    approver_role: Mapped[str] = mapped_column(String(100), nullable=False)
    previous_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    new_status: Mapped[str] = mapped_column(String(30), nullable=False)
    expense_status: Mapped[str] = mapped_column(String(30), nullable=False)
    actor_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
