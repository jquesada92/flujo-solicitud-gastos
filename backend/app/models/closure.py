from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ExpenseClosureDelegation(Base):
    """Auditable delegation of closure/invoice responsibility for one request.

    Only one active row is allowed per expense. Historical rows are retained by
    marking them revoked instead of deleting them.
    """

    __tablename__ = 'expense_closure_delegations'
    __table_args__ = (
        Index('ix_expense_closure_delegations_expense', 'expense_id'),
        Index('ix_expense_closure_delegations_delegate', 'delegate_user_id'),
        Index(
            'uq_expense_closure_delegation_active',
            'expense_id',
            unique=True,
            sqlite_where=text('revoked_at IS NULL'),
            postgresql_where=text('revoked_at IS NULL'),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    expense_id: Mapped[int] = mapped_column(
        ForeignKey('expenses.id', ondelete='CASCADE'),
        nullable=False,
    )
    delegate_user_id: Mapped[int] = mapped_column(
        ForeignKey('users.id', ondelete='RESTRICT'),
        nullable=False,
    )
    delegated_by_user_id: Mapped[int] = mapped_column(
        ForeignKey('users.id', ondelete='RESTRICT'),
        nullable=False,
    )
    delegated_by_email: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey('users.id', ondelete='RESTRICT'),
        nullable=True,
    )
    revoked_by_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
