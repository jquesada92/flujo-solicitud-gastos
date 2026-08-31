import logging
import secrets
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import (
    Approval,
    ApprovalStatus,
    ApprovalStepEvent,
    Expense,
    ExpenseStatus,
)
from app.services.email_service import send_approval_request, send_final_notification
from app.services.approval_policy_service import (
    DIRECT_EXPENSE_REQUIRED_DETAIL,
    find_applicable_policy,
    is_no_approval_policy,
    minimum_votes_for_mode,
    participants_for_policy,
    snapshot_policy_resolution,
)

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
    """Store the event in the same transaction as the approval state change."""
    expense = approval.expense
    event_id = str(uuid.uuid4())
    occurred_at = datetime.now(timezone.utc)
    new_status = _status_value(approval.status)
    expense_status = _status_value(expense.status)
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
            'urgency': expense.urgency,
            'expense_subcategory': expense.expense_subcategory,
            'amount': str(expense.amount),
            'supplier': expense.supplier,
            'requested_by': expense.requested_by,
            'requester_analytics_id': expense.requester_analytics_id,
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


def expire_open_approvals(
    db: Session,
    expense: Expense,
    except_id: int | None = None,
    actor_email: str | None = None,
) -> None:
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


def notify_approval_flow_started(approvals: list[Approval]) -> None:
    """Send notifications only after the caller has committed the workflow."""
    for approval in approvals:
        try:
            if approval.status == ApprovalStatus.PENDING:
                send_approval_request(approval)
        except Exception:
            logger.exception('Approval notification failed; workflow state was already saved')


def start_approval_flow(
    db: Session,
    expense: Expense,
    *,
    commit: bool = True,
) -> list[Approval]:
    amount = Decimal(expense.amount)
    policy = find_applicable_policy(db, expense.expense_type, amount)
    if policy is not None and is_no_approval_policy(policy):
        raise ValueError(DIRECT_EXPENSE_REQUIRED_DETAIL)
    users = participants_for_policy(
        db,
        policy,
        exclude_email=expense.requested_by.lower(),
    )
    if users:
        approval_mode = policy.approval_mode if policy else 'MAJORITY'
        snapshot_policy_resolution(
            expense,
            policy,
            amount,
            len(users),
            default_mode='MAJORITY',
        )
        approvals = [
            Approval(
                expense_id=expense.id,
                flow_id=expense.flow_id,
                approver_email=user.email,
                approver_role='requests:approve',
                step=index,
                approval_mode=approval_mode,
                token=secrets.token_urlsafe(32),
                status=ApprovalStatus.PENDING,
            )
            for index, user in enumerate(users, 1)
        ]
        expense.status = ExpenseStatus.PENDING_APPROVAL
        db.add_all(approvals)
        db.flush()
        for item in approvals:
            record_step_event(db, item, 'STEP_CREATED', None)
        if commit:
            db.commit()
            db.refresh(expense)
            notify_approval_flow_started(approvals)
        return approvals

    raise ValueError(
        'No hay otro usuario activo con permiso efectivo requests:approve para iniciar esta solicitud'
    )


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
    if approval.status != ApprovalStatus.PENDING:
        raise ValueError('Esta acción ya fue procesada y no puede ejecutarse nuevamente')
    if approval.expense.status in (
        ExpenseStatus.CANCELLED,
        ExpenseStatus.CLOSED,
        ExpenseStatus.REJECTED,
        ExpenseStatus.NEEDS_REVISION,
    ):
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

    # A request for revision is an interrupt, not a majority vote. Any assigned
    # approver who detects a problem can stop the active round, explain what the
    # requester must review, and return the request to its owner for correction.
    if decision == ApprovalStatus.REVISION_REQUESTED:
        expense.status = ExpenseStatus.NEEDS_REVISION
        record_step_event(
            db,
            approval,
            'STEP_REVISION_REQUESTED',
            previous_status,
            actor_email=actor_email,
            comment=comment,
        )
        expire_open_approvals(db, expense, approval.id, actor_email)
        db.commit()
        db.refresh(expense)
        _safe_email(send_final_notification, expense)
        return expense

    if approval.approval_mode in ('ANY', 'ALL', 'MAJORITY'):
        peers = [a for a in expense.approvals if a.flow_id == approval.flow_id]
        record_step_event(
            db,
            approval,
            f'STEP_{decision.value}',
            previous_status,
            actor_email=actor_email,
            comment=comment,
        )
        threshold = minimum_votes_for_mode(approval.approval_mode, len(peers))
        approved_count = sum(a.status == ApprovalStatus.APPROVED for a in peers)
        rejected_count = sum(a.status == ApprovalStatus.REJECTED for a in peers)
        if approved_count >= threshold:
            expense.status = ExpenseStatus.APPROVED
            expire_open_approvals(db, expense, approval.id, actor_email)
        # Reject only when the remaining PENDING votes can no longer reach the
        # configured approval threshold. Thus ALL rejects on one rejection,
        # ANY rejects only when everyone rejects, and MAJORITY is symmetric.
        elif rejected_count > len(peers) - threshold:
            expense.status = ExpenseStatus.REJECTED
            expire_open_approvals(db, expense, approval.id, actor_email)
        db.commit()
        db.refresh(expense)
        if expense.status != ExpenseStatus.PENDING_APPROVAL:
            _safe_email(send_final_notification, expense)
        return expense

    if decision == ApprovalStatus.REJECTED:
        expense.status = ExpenseStatus.REJECTED
        record_step_event(db, approval, 'STEP_REJECTED', previous_status, actor_email=actor_email, comment=comment)
        expire_open_approvals(db, expense, approval.id, actor_email)
        db.commit()
        db.refresh(expense)
        _safe_email(send_final_notification, expense)
        return expense

    next_approval = next(
        (
            a
            for a in expense.approvals
            if a.step > approval.step and a.status == ApprovalStatus.WAITING
        ),
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
