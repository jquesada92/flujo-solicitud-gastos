from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.closure import ExpenseClosureDelegation
from app.models.entities import Expense, ExpenseStatus, User
from app.models.iam import SystemAccount
from app.services.iam_service import is_system_account


def is_closure_actionable(expense: Expense) -> bool:
    if expense.status == ExpenseStatus.CLOSED:
        return True
    if expense.request_type == 'MULTI_QUOTE':
        return (
            expense.status == ExpenseStatus.QUOTATION_VOTING
            and expense.selected_quotation_id is not None
        )
    return expense.status == ExpenseStatus.APPROVED


def is_requester(expense: Expense, user: User) -> bool:
    return (expense.requested_by or '').strip().lower() == (user.email or '').strip().lower()


def active_closure_delegation(
    db: Session,
    expense_id: int,
) -> ExpenseClosureDelegation | None:
    return db.scalar(
        select(ExpenseClosureDelegation).where(
            ExpenseClosureDelegation.expense_id == expense_id,
            ExpenseClosureDelegation.revoked_at.is_(None),
        )
    )


def can_manage_closure(
    db: Session,
    expense: Expense,
    user: User,
    *,
    system_admin: bool | None = None,
) -> bool:
    """Authorize close/invoice operations for one concrete request.

    The global ``requests:close`` permission is intentionally not consulted.
    Authority belongs to the original requester, the protected system account,
    or the active per-request delegate chosen by the requester.
    """
    if not is_closure_actionable(expense):
        return False
    if is_requester(expense, user):
        return True
    technical_admin = is_system_account(db, user.id) if system_admin is None else system_admin
    if technical_admin:
        return True
    delegation = active_closure_delegation(db, expense.id)
    if not delegation or delegation.delegate_user_id != user.id or not user.active:
        return False
    return True


def can_delegate_closure(expense: Expense, user: User) -> bool:
    """Only the original requester may create/revoke a delegation."""
    return is_closure_actionable(expense) and is_requester(expense, user)


def closure_delegation_candidates(db: Session, expense: Expense) -> list[User]:
    """Return active non-system users that the requester may delegate to."""
    requester = (expense.requested_by or '').strip().lower()
    system_user_ids = select(SystemAccount.user_id)
    stmt = (
        select(User)
        .where(
            User.active.is_(True),
            func.lower(User.email) != requester,
            ~User.id.in_(system_user_ids),
        )
        .order_by(User.name, User.email)
    )
    return list(db.scalars(stmt).all())


def assign_closure_delegate(
    db: Session,
    expense: Expense,
    requester: User,
    delegate: User,
) -> ExpenseClosureDelegation:
    if not can_delegate_closure(expense, requester):
        raise ValueError('Solo el solicitante original puede delegar el cierre o manejo de factura')
    if not delegate.active:
        raise ValueError('El usuario delegado debe estar activo')
    if is_requester(expense, delegate):
        raise ValueError('El solicitante ya tiene autorización de cierre y no necesita delegarse a sí mismo')
    if is_system_account(db, delegate.id):
        raise ValueError('El Administrador del sistema ya tiene esta facultad y no necesita una delegación')

    current = active_closure_delegation(db, expense.id)
    if current and current.delegate_user_id == delegate.id:
        return current
    if current:
        current.revoked_at = datetime.now(timezone.utc)
        current.revoked_by_user_id = requester.id
        current.revoked_by_email = requester.email
        # Release the partial unique index before inserting the new active row.
        db.flush()

    delegation = ExpenseClosureDelegation(
        expense_id=expense.id,
        delegate_user_id=delegate.id,
        delegated_by_user_id=requester.id,
        delegated_by_email=requester.email,
    )
    db.add(delegation)
    db.flush()
    return delegation


def revoke_closure_delegate(
    db: Session,
    expense: Expense,
    requester: User,
) -> ExpenseClosureDelegation | None:
    if not can_delegate_closure(expense, requester):
        raise ValueError('Solo el solicitante original puede revocar la delegación de cierre o factura')
    current = active_closure_delegation(db, expense.id)
    if not current:
        return None
    current.revoked_at = datetime.now(timezone.utc)
    current.revoked_by_user_id = requester.id
    current.revoked_by_email = requester.email
    db.flush()
    return current
