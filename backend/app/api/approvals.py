import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload
from app.core.database import get_db
from app.core.privacy import can_view_personal_data, mask_email
from app.core.security import current_user, require_permission
from app.models.entities import Approval, ApprovalStatus, Expense, ExpenseAttachment, ExpenseStatus, User, UserRole
from app.schemas.approval import ApprovalDecision
from app.schemas.expense import ExpenseOut
from app.services.approval_engine import apply_decision

router = APIRouter()
UPLOAD_DIR = Path(os.getenv('UPLOAD_DIR', '/app/uploads'))


def _approval_by_token(db: Session, token: str) -> Approval:
    stmt = select(Approval).where(Approval.token == token).options(joinedload(Approval.expense))
    approval = db.scalars(stmt).first()
    if not approval:
        raise HTTPException(status_code=404, detail='Approval link not found')
    return approval


def _ensure_link_is_current(approval: Approval) -> None:
    if approval.status == ApprovalStatus.EXPIRED:
        raise HTTPException(status_code=410, detail='Esta aprobación ya no está vigente porque el flujo terminó o fue reemplazado')
    if approval.expense.status in (ExpenseStatus.CANCELLED, ExpenseStatus.CLOSED):
        raise HTTPException(status_code=410, detail='Esta aprobación ya no está vigente porque la solicitud no tiene un flujo activo')


@router.get('/email/{token}')
def get_email_approval(token: str, db: Session = Depends(get_db)):
    approval = _approval_by_token(db, token)
    _ensure_link_is_current(approval)
    expense = approval.expense
    return {'kind': 'APPROVAL', 'token': token, 'status': approval.status.value,
            'approver_role': approval.approver_role,
            'expense': {'display_id': expense.display_id, 'title': expense.title,
                        'description': expense.description, 'supplier': expense.supplier,
                        'amount': str(expense.amount), 'urgency': expense.urgency,
                        'expense_type': expense.expense_type,
                        'expense_subcategory': expense.expense_subcategory,
                        'item_url': expense.item_url,
                        'attachments': [{'id': item.id, 'original_name': item.original_name,
                                         'content_type': item.content_type, 'size': item.size}
                                        for item in expense.attachments]}}


@router.get('/email/{token}/attachments/{attachment_id}')
def view_email_approval_attachment(token: str, attachment_id: int, db: Session = Depends(get_db)):
    approval = _approval_by_token(db, token)
    _ensure_link_is_current(approval)
    attachment = db.scalar(select(ExpenseAttachment).where(
        ExpenseAttachment.id == attachment_id,
        ExpenseAttachment.expense_id == approval.expense_id))
    if not attachment:
        raise HTTPException(status_code=404, detail='Cotización no encontrada')
    path = UPLOAD_DIR / attachment.stored_name
    if not path.is_file():
        raise HTTPException(status_code=404, detail='El archivo ya no está disponible')
    return FileResponse(path, media_type=attachment.content_type,
                        filename=attachment.original_name, content_disposition_type='inline')


@router.post('/email/{token}')
def decide_email_approval(token: str, payload: ApprovalDecision, db: Session = Depends(get_db)):
    approval = db.scalar(select(Approval).where(Approval.token == token).options(selectinload(Approval.expense)))
    if not approval:
        raise HTTPException(status_code=404, detail='Enlace de aprobación no encontrado')
    db.scalar(select(Expense).where(Expense.id == approval.expense_id).with_for_update())
    db.refresh(approval); _ensure_link_is_current(approval)
    try:
        expense = apply_decision(db, approval, ApprovalStatus(payload.decision), payload.comment, approval.approver_email)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {'status': expense.status.value, 'decision': payload.decision, 'display_id': expense.display_id}


@router.get('/{token}')
def get_approval(token: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    approval = _approval_by_token(db, token)
    _ensure_link_is_current(approval)
    if user.role != UserRole.ADMIN and (not user.can_approve or user.email != approval.approver_email.lower()):
        raise HTTPException(status_code=403, detail='Esta aprobación no está asignada a tu usuario')
    expense = approval.expense
    return {
        'approval_id': approval.id,
        'approver_role': approval.approver_role,
        'approver_email': approval.approver_email if can_view_personal_data(user) else mask_email(approval.approver_email),
        'approval_status': approval.status.value,
        'expense': {
            'id': expense.id,
            'request_id': expense.request_id,
            'flow_id': expense.flow_id,
            'display_id': expense.display_id,
            'title': expense.title,
            'description': expense.description,
            'expense_type': expense.expense_type,
            'expense_subcategory': expense.expense_subcategory,
            'urgency': expense.urgency,
            'amount': str(expense.amount),
            'supplier': expense.supplier,
            'item_url': expense.item_url,
            'attachments': [
                {
                    'id': attachment.id,
                    'original_name': attachment.original_name,
                    'content_type': attachment.content_type,
                    'size': attachment.size,
                }
                for attachment in expense.attachments
            ],
            'requested_by': expense.requested_by if can_view_personal_data(user) else mask_email(expense.requested_by),
            'status': expense.status.value,
        },
    }


@router.post('/{token}', response_model=ExpenseOut)
def decide_approval(
    token: str,
    payload: ApprovalDecision,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission('can_approve')),
):
    stmt = select(Approval).where(Approval.token == token).options(selectinload(Approval.expense))
    approval = db.scalars(stmt).first()
    if not approval:
        raise HTTPException(status_code=404, detail='Enlace de aprobación no encontrado')
    db.scalar(select(Expense).where(Expense.id == approval.expense_id).with_for_update())
    db.refresh(approval)
    _ensure_link_is_current(approval)
    if user.email.lower() == approval.expense.requested_by.lower():
        raise HTTPException(status_code=403, detail='No puedes aprobar tu propia solicitud')
    if user.role != UserRole.ADMIN and user.email != approval.approver_email.lower():
        raise HTTPException(status_code=403, detail='Esta aprobación no está asignada a tu usuario')
    try:
        expense = apply_decision(db, approval, ApprovalStatus(payload.decision), payload.comment, user.email)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    stmt = select(Expense).where(Expense.id == expense.id).options(selectinload(Expense.approvals))
    return db.scalars(stmt).one()
