import enum
import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class ExpenseStatus(str, enum.Enum):
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
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    can_request: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    can_approve: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    can_view: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    can_configure: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Expense(Base):
    __tablename__ = 'expenses'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    flow_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    display_id: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    revised_from_request_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    expense_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    expense_subcategory: Mapped[str | None] = mapped_column(String(80), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    supplier: Mapped[str] = mapped_column(String(200), nullable=False)
    item_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    requested_by: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[ExpenseStatus] = mapped_column(Enum(ExpenseStatus), default=ExpenseStatus.SUBMITTED, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancelled_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    closed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    closure_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    approvals = relationship('Approval', back_populates='expense', cascade='all, delete-orphan', order_by='Approval.step')
    attachments = relationship('ExpenseAttachment', back_populates='expense', cascade='all, delete-orphan')


class CategoryCounter(Base):
    __tablename__ = 'category_counters'

    category: Mapped[str] = mapped_column(String(80), primary_key=True)
    last_value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class ExpenseCategory(Base):
    __tablename__ = 'expense_categories'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    subcategories = relationship('ExpenseSubcategory', back_populates='category', cascade='all, delete-orphan', order_by='ExpenseSubcategory.name')


class ExpenseSubcategory(Base):
    __tablename__ = 'expense_subcategories'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey('expense_categories.id', ondelete='CASCADE'), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    category = relationship('ExpenseCategory', back_populates='subcategories')


class ExpenseAttachment(Base):
    __tablename__ = 'expense_attachments'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    expense_id: Mapped[int] = mapped_column(ForeignKey('expenses.id', ondelete='CASCADE'), nullable=False, index=True)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    document_type: Mapped[str] = mapped_column(String(40), nullable=False, default='QUOTATION')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    expense = relationship('Expense', back_populates='attachments')


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


class Approval(Base):
    __tablename__ = 'approvals'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    expense_id: Mapped[int] = mapped_column(ForeignKey('expenses.id', ondelete='CASCADE'), nullable=False, index=True)
    flow_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    approver_email: Mapped[str] = mapped_column(String(255), nullable=False)
    approver_role: Mapped[str] = mapped_column(String(100), nullable=False)
    step: Mapped[int] = mapped_column(Integer, nullable=False)
    token: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    status: Mapped[ApprovalStatus] = mapped_column(Enum(ApprovalStatus), default=ApprovalStatus.WAITING, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    expense = relationship('Expense', back_populates='approvals')
