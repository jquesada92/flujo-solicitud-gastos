from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload
from app.core.database import get_db
from app.core.security import current_user, require_roles
from app.models.entities import Approval, ApprovalStatus, Expense, ExpenseStatus, User, UserRole
from app.schemas.approval import ApprovalDecision
from app.schemas.expense import ExpenseOut
from app.services.approval_engine import apply_decision

router = APIRouter()


def _approval_by_token(db: Session, token: str) -> Approval:
    stmt = select(Approval).where(Approval.token == token).options(joinedload(Approval.expense))
    approval = db.scalars(stmt).first()
    if not approval:
        raise HTTPException(status_code=404, detail='Approval link not found')
    return approval


def _ensure_link_is_current(approval: Approval) -> None:
    if approval.status == ApprovalStatus.EXPIRED:
        raise HTTPException(status_code=410, detail='Este enlace expiró porque el flujo fue cancelado, rechazado o reemplazado por una corrección')
    if approval.expense.status in (ExpenseStatus.CANCELLED, ExpenseStatus.CLOSED):
        raise HTTPException(status_code=410, detail='Este enlace expiró porque la solicitud ya no tiene un flujo activo')


@router.get('/{token}')
def get_approval(token: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    approval = _approval_by_token(db, token)
    _ensure_link_is_current(approval)
    if user.role != UserRole.ADMIN and (user.role != UserRole.APPROVER or user.email != approval.approver_email.lower()):
        raise HTTPException(status_code=403, detail='Esta aprobación no está asignada a tu usuario')
    expense = approval.expense
    return {
        'approval_id': approval.id,
        'approver_role': approval.approver_role,
        'approver_email': approval.approver_email,
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
            'requested_by': expense.requested_by,
            'status': expense.status.value,
        },
    }


@router.post('/{token}', response_model=ExpenseOut)
def decide_approval(
    token: str,
    payload: ApprovalDecision,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.APPROVER, UserRole.ADMIN)),
):
    stmt = select(Approval).where(Approval.token == token).options(selectinload(Approval.expense))
    approval = db.scalars(stmt).first()
    if not approval:
        raise HTTPException(status_code=404, detail='Enlace de aprobación no encontrado')
    db.scalar(select(Expense).where(Expense.id == approval.expense_id).with_for_update())
    db.refresh(approval)
    _ensure_link_is_current(approval)
    if user.role != UserRole.ADMIN and user.email != approval.approver_email.lower():
        raise HTTPException(status_code=403, detail='Esta aprobación no está asignada a tu usuario')
    try:
        expense = apply_decision(db, approval, ApprovalStatus(payload.decision), payload.comment)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    stmt = select(Expense).where(Expense.id == expense.id).options(selectinload(Expense.approvals))
    return db.scalars(stmt).one()
