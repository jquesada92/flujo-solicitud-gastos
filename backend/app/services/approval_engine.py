import logging
import secrets
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session
from app.models.entities import Approval, ApprovalPolicy, ApprovalRule, ApprovalStatus, ApprovalStepEvent, Expense, ExpenseStatus, User, UserRole
from app.services.email_service import send_approval_request, send_final_notification

logger = logging.getLogger(__name__)


def _status_value(value) -> str:
    return value.value if hasattr(value, 'value') else str(value)


def record_step_event(db: Session, approval: Approval, event_type: str,
                      previous_status: ApprovalStatus | None, *,
                      actor_email: str | None = None, comment: str | None = None) -> None:
    """Store the event in the same transaction as the approval state change."""
    expense = approval.expense
    event_id = str(uuid.uuid4())
    occurred_at = datetime.now(timezone.utc)
    new_status = _status_value(approval.status)
    expense_status = _status_value(expense.status)
    payload = {
        'schema_version': 1, 'event_id': event_id, 'occurred_at': occurred_at.isoformat(),
        'event_type': event_type,
        'request': {
            'expense_id': expense.id, 'request_id': expense.request_id,
            'display_id': expense.display_id, 'flow_id': approval.flow_id,
            'title': expense.title, 'expense_type': expense.expense_type, 'urgency': expense.urgency,
            'expense_subcategory': expense.expense_subcategory, 'amount': str(expense.amount),
            'supplier': expense.supplier, 'requested_by': expense.requested_by,
            'requester_analytics_id': expense.requester_analytics_id,
            'status': expense_status,
        },
        'approval_step': {
            'approval_id': approval.id, 'step': approval.step,
            'approver_email': approval.approver_email, 'approver_role': approval.approver_role,
            'previous_status': _status_value(previous_status) if previous_status else None,
            'new_status': new_status, 'actor_email': actor_email, 'comment': comment,
        },
    }
    db.add(ApprovalStepEvent(
        event_id=event_id, occurred_at=occurred_at, event_type=event_type,
        expense_id=expense.id, approval_id=approval.id, request_id=expense.request_id,
        display_id=expense.display_id, flow_id=approval.flow_id, step=approval.step,
        approver_email=approval.approver_email, approver_role=approval.approver_role,
        previous_status=_status_value(previous_status) if previous_status else None,
        new_status=new_status, expense_status=expense_status, actor_email=actor_email,
        comment=comment, payload=payload,
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
    amount = Decimal(expense.amount)
    policies = list(db.scalars(select(ApprovalPolicy).where(
        ApprovalPolicy.active.is_(True),
        ApprovalPolicy.expense_type.in_([expense.expense_type, 'ALL']),
        ApprovalPolicy.min_amount <= amount,
        or_(ApprovalPolicy.max_amount.is_(None), ApprovalPolicy.max_amount >= amount),
    ).order_by(ApprovalPolicy.expense_type.desc())).all())
    if policies:
        policy = next((p for p in policies if p.expense_type == expense.expense_type), policies[0])
        # Every active board member participates. The requester is always
        # excluded, so an ALL policy requires N-1 approvals when the requester
        # is one of the N members of the board.
        users = list(db.scalars(select(User).where(
            User.active.is_(True), User.can_approve.is_(True), User.role != UserRole.ADMIN,
            User.title.in_(policy.approver_profile_codes),
            func.lower(User.email) != expense.requested_by.lower(),
        ).order_by(User.id)).all())
        if not users:
            raise ValueError(
                'La regla aplicable no tiene otro usuario activo que pueda aprobar esta solicitud'
            )
        approvals = [Approval(expense_id=expense.id, flow_id=expense.flow_id, approver_email=user.email,
            approver_role=user.title, step=index, approval_mode='MAJORITY',
            token=secrets.token_urlsafe(32), status=ApprovalStatus.PENDING)
            for index, user in enumerate(users, 1)]
        expense.status = ExpenseStatus.PENDING_APPROVAL
        db.add_all(approvals); db.flush()
        for item in approvals: record_step_event(db, item, 'STEP_CREATED', None)
        db.commit(); db.refresh(expense)
        for item in approvals: _safe_email(send_approval_request, item)
        return

    rules = [
        rule
        for rule in matching_rules(db, expense)
        if rule.approver_email.lower() != expense.requested_by.lower()
    ]
    if not rules:
        raise ValueError(
            'La regla aplicable no tiene otro usuario que pueda aprobar esta solicitud'
        )

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
        raise ValueError('Esta aprobación ya no está vigente porque el flujo terminó o fue reemplazado')
    if approval.status not in (ApprovalStatus.PENDING, ApprovalStatus.APPROVED,
                               ApprovalStatus.REJECTED, ApprovalStatus.REVISION_REQUESTED):
        raise ValueError('Esta acción ya fue procesada y no puede ejecutarse nuevamente')
    if approval.expense.status in (ExpenseStatus.CANCELLED, ExpenseStatus.CLOSED, ExpenseStatus.REJECTED, ExpenseStatus.NEEDS_REVISION):
        expire_open_approvals(db, approval.expense)
        db.commit()
        raise ValueError('Esta aprobación ya no está vigente porque la solicitud no tiene un flujo activo')

    if decision == ApprovalStatus.REVISION_REQUESTED and (not comment or len(comment.strip()) < 3):
        raise ValueError('Debes indicar qué debe corregir el solicitante')
    previous_status = approval.status
    approval.status = decision
    approval.comment = comment
    approval.decided_at = datetime.utcnow()
    expense = approval.expense

    if approval.approval_mode in ('ANY', 'ALL', 'MAJORITY'):
        peers = [a for a in expense.approvals if a.flow_id == approval.flow_id]
        record_step_event(db, approval, f'STEP_{decision.value}', previous_status, actor_email=actor_email, comment=comment)
        threshold = len(peers) // 2 + 1
        approved_count = sum(a.status == ApprovalStatus.APPROVED for a in peers)
        rejected_count = sum(a.status == ApprovalStatus.REJECTED for a in peers)
        revision_count = sum(a.status == ApprovalStatus.REVISION_REQUESTED for a in peers)
        if approved_count >= threshold:
            expense.status = ExpenseStatus.APPROVED
            expire_open_approvals(db, expense, approval.id, actor_email)
        elif rejected_count >= threshold:
            expense.status = ExpenseStatus.REJECTED
            expire_open_approvals(db, expense, approval.id, actor_email)
        elif revision_count >= threshold:
            expense.status = ExpenseStatus.NEEDS_REVISION
            expire_open_approvals(db, expense, approval.id, actor_email)
        db.commit(); db.refresh(expense)
        if expense.status != ExpenseStatus.PENDING_APPROVAL: _safe_email(send_final_notification, expense)
        return expense

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
