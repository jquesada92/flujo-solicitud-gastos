from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.security import require_permission
from app.models.entities import Approval, ApprovalStatus, Expense, User
from app.schemas.approval import ApprovalDecision
from app.services.approval_engine import apply_decision
from app.services.pending_action_service import (
    APPROVAL_DECISION,
    CLOSE_REQUEST,
    CORRECT_REQUEST,
    QUOTATION_VOTE,
    pending_actions_by_expense,
)

router = APIRouter()

ACTION_LABELS = {
    APPROVAL_DECISION: 'Responder aprobación',
    QUOTATION_VOTE: 'Votar cotización',
    CLOSE_REQUEST: 'Subir factura y cerrar',
    CORRECT_REQUEST: 'Corregir y reenviar',
}


def _expense(db: Session, request_id: str) -> Expense:
    expense = db.scalar(
        select(Expense)
        .where(or_(Expense.request_id == request_id, Expense.display_id == request_id))
        .options(
            selectinload(Expense.attachments),
            selectinload(Expense.quotation_options),
            selectinload(Expense.quotation_votes),
            selectinload(Expense.approvals),
        )
    )
    if not expense:
        raise HTTPException(status_code=404, detail='Solicitud no encontrada')
    return expense


def _attachment(item) -> dict:
    return {
        'id': item.id,
        'original_name': item.original_name,
        'content_type': item.content_type,
        'size': item.size,
        'document_type': item.document_type,
        'quotation_option_id': item.quotation_option_id,
    }


def _request_payload(expense: Expense) -> dict:
    general_supports = [
        _attachment(item)
        for item in expense.attachments
        if item.quotation_option_id is None and item.document_type != 'INVOICE_REPLACED'
    ]
    return {
        'request_id': expense.request_id,
        'display_id': expense.display_id,
        'flow_id': expense.flow_id,
        'request_type': expense.request_type,
        'title': expense.title,
        'description': expense.description,
        'expense_type': expense.expense_type,
        'expense_subcategory': expense.expense_subcategory,
        'urgency': expense.urgency,
        'amount': str(expense.amount) if expense.amount is not None else None,
        'supplier': expense.supplier,
        'item_url': expense.item_url,
        'status': expense.status.value,
        'supports': general_supports,
        'quotation_options': [
            {
                'id': option.id,
                'option_number': option.option_number,
                'supplier': option.supplier,
                'amount': str(option.amount),
                'item_url': option.item_url,
                'notes': option.notes,
                'supports': [
                    _attachment(item)
                    for item in expense.attachments
                    if item.quotation_option_id == option.id
                    and item.document_type != 'INVOICE_REPLACED'
                ],
            }
            for option in expense.quotation_options
        ],
    }


@router.get('/{request_id}/my-actions')
def get_my_request_actions(
    request_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission('requests:read')),
):
    """Return only actions that are currently executable by the logged-in user."""
    expense = _expense(db, request_id)
    action_codes = pending_actions_by_expense(db, user, expense_ids=[expense.id]).get(expense.id, [])
    return {
        'request': _request_payload(expense),
        'actions': [
            {'code': code, 'label': ACTION_LABELS[code]}
            for code in action_codes
        ],
    }


@router.post('/{request_id}/approval-decision')
def decide_my_approval(
    request_id: str,
    payload: ApprovalDecision,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission('requests:approve')),
):
    """Register the current user's pending approval without exposing bearer-link tokens."""
    expense = db.scalar(
        select(Expense)
        .where(or_(Expense.request_id == request_id, Expense.display_id == request_id))
        .with_for_update()
    )
    if not expense:
        raise HTTPException(status_code=404, detail='Solicitud no encontrada')
    if expense.requested_by.lower() == user.email.lower():
        raise HTTPException(status_code=403, detail='No puedes aprobar tu propia solicitud')

    approval = db.scalar(
        select(Approval).where(
            Approval.expense_id == expense.id,
            func.lower(Approval.approver_email) == user.email.lower(),
            Approval.status == ApprovalStatus.PENDING,
        )
    )
    if not approval:
        raise HTTPException(
            status_code=409,
            detail='Ya no tienes una aprobación pendiente para esta solicitud',
        )

    try:
        updated = apply_decision(
            db,
            approval,
            ApprovalStatus(payload.decision),
            payload.comment,
            user.email,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return {
        'display_id': updated.display_id,
        'status': updated.status.value,
        'decision': payload.decision,
    }
