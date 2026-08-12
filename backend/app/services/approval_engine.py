import logging
import secrets
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session
from app.models.entities import Approval, ApprovalRule, ApprovalStatus, ApprovalStepEvent, Expense, ExpenseStatus
from app.services.email_service import send_approval_request, send_final_notification

logger = logging.getLogger(__name__)


def _status_value(value) -> str:
    return value.value if hasattr(value, 'value') else str(value)


def record_step_event(
    db: Session,
    approval: Approval,
    event_type: str,
    previous_status: ApprovalStatus | None,
    *,
    actor_email: str | None = None,
    comment: str | None = None,
) -> None:
    """Write the immutable event in the same transaction as its state change."""
    expense = approval.expense
    new_status = _status_value(approval.status)
    expense_status = _status_value(expense.status)
    event_id = str(uuid.uuid4())
    occurred_at = datetime.now(timezone.utc)
    payload = {
        'schema_version': 1,
        'event_id': event_id,
        'occurred_at': occurred_at.isoformat(),
        'event_type': event_type,
        'request': {
            'expense_id': expense.id,
            'request_id': expense.request_id,
            'display_id': expense.display_id,
            'flow_id': approval.flow_id,
            'title': expense.title,
            'expense_type': expense.expense_type,
            'expense_subcategory': expense.expense_subcategory,
            'amount': str(expense.amount),
            'supplier': expense.supplier,
            'requested_by': expense.requested_by,
            'status': expense_status,
        },
        'approval_step': {
            'approval_id': approval.id,
            'step': approval.step,
            'approver_email': approval.approver_email,
            'approver_role': approval.approver_role,
            'previous_status': _status_value(previous_status) if previous_status else None,
            'new_status': new_status,
            'actor_email': actor_email,
            'comment': comment,
        },
    }
    db.add(ApprovalStepEvent(
        event_id=event_id,
        occurred_at=occurred_at,
        event_type=event_type,
        expense_id=expense.id,
        approval_id=approval.id,
        request_id=expense.request_id,
        display_id=expense.display_id,
        flow_id=approval.flow_id,
        step=approval.step,
        approver_email=approval.approver_email,
        approver_role=approval.approver_role,
        previous_status=_status_value(previous_status) if previous_status else None,
        new_status=new_status,
        expense_status=expense_status,
        actor_email=actor_email,
        comment=comment,
        payload=payload,
    ))


def expire_open_approvals(db: Session, expense: Expense, except_id: int | None = None, actor_email: str | None = None) -> None:
    """Invalidate every unused link belonging to an obsolete workflow version."""
    for item in expense.approvals:
        if item.id != except_id and item.status in (ApprovalStatus.PENDING, ApprovalStatus.WAITING):
            previous = item.status
            item.status = ApprovalStatus.EXPIRED
            record_step_event(db, item, 'STEP_EXPIRED', previous, actor_email=actor_email)


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
    db.flush()
    for approval in approvals:
        record_step_event(db, approval, 'STEP_CREATED', None)
    db.commit()
    db.refresh(expense)

    first = next(a for a in expense.approvals if a.status == ApprovalStatus.PENDING)
    _safe_email(send_approval_request, first)


def apply_decision(
    db: Session,
    approval: Approval,
    decision: ApprovalStatus,
    comment: str | None,
    actor_email: str | None = None,
) -> Expense:
    from datetime import datetime

    if approval.status == ApprovalStatus.EXPIRED:
        raise ValueError('Este enlace expiró porque el flujo fue cancelado, rechazado o reemplazado por una corrección')
    if approval.status != ApprovalStatus.PENDING:
        raise ValueError('Esta acción ya fue procesada y no puede ejecutarse nuevamente')
    if approval.expense.status in (ExpenseStatus.CANCELLED, ExpenseStatus.CLOSED, ExpenseStatus.REJECTED, ExpenseStatus.NEEDS_REVISION):
        expire_open_approvals(db, approval.expense)
        db.commit()
        raise ValueError('Este enlace expiró porque la solicitud ya no tiene un flujo activo')

    previous_status = approval.status
    approval.status = decision
    approval.comment = comment
    approval.decided_at = datetime.utcnow()
    expense = approval.expense

    if decision == ApprovalStatus.REJECTED:
        expense.status = ExpenseStatus.REJECTED
        record_step_event(db, approval, 'STEP_REJECTED', previous_status, actor_email=actor_email, comment=comment)
        expire_open_approvals(db, expense, approval.id, actor_email)
        db.commit()
        db.refresh(expense)
        _safe_email(send_final_notification, expense)
        return expense

    if decision == ApprovalStatus.REVISION_REQUESTED:
        if not comment or len(comment.strip()) < 3:
            raise ValueError('Debes indicar qué debe corregir el solicitante')
        expense.status = ExpenseStatus.NEEDS_REVISION
        record_step_event(db, approval, 'STEP_REVISION_REQUESTED', previous_status, actor_email=actor_email, comment=comment)
        expire_open_approvals(db, expense, approval.id, actor_email)
        db.commit()
        db.refresh(expense)
        _safe_email(send_final_notification, expense)
        return expense

    next_approval = next(
        (a for a in expense.approvals if a.step > approval.step and a.status == ApprovalStatus.WAITING),
        None,
    )

    if next_approval:
        record_step_event(db, approval, 'STEP_APPROVED', previous_status, actor_email=actor_email, comment=comment)
        next_previous = next_approval.status
        next_approval.status = ApprovalStatus.PENDING
        record_step_event(db, next_approval, 'STEP_ACTIVATED', next_previous)
        db.commit()
        db.refresh(next_approval)
        _safe_email(send_approval_request, next_approval)
    else:
        expense.status = ExpenseStatus.APPROVED
        record_step_event(db, approval, 'STEP_APPROVED', previous_status, actor_email=actor_email, comment=comment)
        db.commit()
        db.refresh(expense)
        _safe_email(send_final_notification, expense)

    return expense
