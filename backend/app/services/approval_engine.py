import logging
import secrets
from decimal import Decimal
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session
from app.models.entities import Approval, ApprovalRule, ApprovalStatus, Expense, ExpenseStatus
from app.services.email_service import send_approval_request, send_final_notification

logger = logging.getLogger(__name__)


def expire_open_approvals(expense: Expense, except_id: int | None = None) -> None:
    """Invalidate every unused link belonging to an obsolete workflow version."""
    for item in expense.approvals:
        if item.id != except_id and item.status in (ApprovalStatus.PENDING, ApprovalStatus.WAITING):
            item.status = ApprovalStatus.EXPIRED


def _safe_email(callable_, *args) -> None:
    try:
        callable_(*args)
    except Exception:
        logger.exception('Email delivery failed; workflow state was still saved')


def matching_rules(db: Session, expense: Expense) -> list[ApprovalRule]:
    amount = Decimal(expense.amount)
    stmt = (
        select(ApprovalRule)
        .where(
            ApprovalRule.active.is_(True),
            ApprovalRule.expense_type == expense.expense_type,
            ApprovalRule.min_amount <= amount,
            or_(ApprovalRule.max_amount.is_(None), ApprovalRule.max_amount >= amount),
        )
        .order_by(ApprovalRule.step.asc())
    )
    return list(db.scalars(stmt).all())


def start_approval_flow(db: Session, expense: Expense) -> None:
    rules = matching_rules(db, expense)
    if not rules:
        raise ValueError(f'No approval rule configured for type={expense.expense_type} amount={expense.amount}')

    approvals: list[Approval] = []
    for index, rule in enumerate(rules):
        approvals.append(
            Approval(
                expense_id=expense.id,
                flow_id=expense.flow_id,
                approver_email=rule.approver_email,
                approver_role=rule.approver_role,
                step=rule.step,
                token=secrets.token_urlsafe(32),
                status=ApprovalStatus.PENDING if index == 0 else ApprovalStatus.WAITING,
            )
        )

    expense.status = ExpenseStatus.PENDING_APPROVAL
    db.add_all(approvals)
    db.commit()
    db.refresh(expense)

    first = next(a for a in expense.approvals if a.status == ApprovalStatus.PENDING)
    _safe_email(send_approval_request, first)


def apply_decision(db: Session, approval: Approval, decision: ApprovalStatus, comment: str | None) -> Expense:
    from datetime import datetime

    if approval.status == ApprovalStatus.EXPIRED:
        raise ValueError('Este enlace expiró porque el flujo fue cancelado, rechazado o reemplazado por una corrección')
    if approval.status != ApprovalStatus.PENDING:
        raise ValueError('Esta acción ya fue procesada y no puede ejecutarse nuevamente')
    if approval.expense.status in (ExpenseStatus.CANCELLED, ExpenseStatus.CLOSED, ExpenseStatus.REJECTED, ExpenseStatus.NEEDS_REVISION):
        expire_open_approvals(approval.expense)
        db.commit()
        raise ValueError('Este enlace expiró porque la solicitud ya no tiene un flujo activo')

    approval.status = decision
    approval.comment = comment
    approval.decided_at = datetime.utcnow()
    expense = approval.expense

    if decision == ApprovalStatus.REJECTED:
        expense.status = ExpenseStatus.REJECTED
        expire_open_approvals(expense, approval.id)
        db.commit()
        db.refresh(expense)
        _safe_email(send_final_notification, expense)
        return expense

    if decision == ApprovalStatus.REVISION_REQUESTED:
        if not comment or len(comment.strip()) < 3:
            raise ValueError('Debes indicar qué debe corregir el solicitante')
        expense.status = ExpenseStatus.NEEDS_REVISION
        expire_open_approvals(expense, approval.id)
        db.commit()
        db.refresh(expense)
        _safe_email(send_final_notification, expense)
        return expense

    next_approval = next(
        (a for a in expense.approvals if a.step > approval.step and a.status == ApprovalStatus.WAITING),
        None,
    )

    if next_approval:
        next_approval.status = ApprovalStatus.PENDING
        db.commit()
        db.refresh(next_approval)
        _safe_email(send_approval_request, next_approval)
    else:
        expense.status = ExpenseStatus.APPROVED
        db.commit()
        db.refresh(expense)
        _safe_email(send_final_notification, expense)

    return expense
