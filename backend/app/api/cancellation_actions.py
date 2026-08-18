from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.security import current_user
from app.models.entities import Expense, ExpenseStatus, User
from app.schemas.expense import ExpenseOut
from app.services.approval_engine import expire_open_approvals
from app.services.iam_service import is_system_account

router = APIRouter()

OPEN_CANCELLABLE_STATUSES = {
    ExpenseStatus.QUOTATION_VOTING,
    ExpenseStatus.SUBMITTED,
    ExpenseStatus.PENDING_APPROVAL,
    ExpenseStatus.NEEDS_REVISION,
    ExpenseStatus.APPROVED,
}


class CancellationRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


def can_cancel_expense(
    db: Session,
    expense: Expense,
    user: User,
    *,
    system_admin: bool | None = None,
) -> bool:
    """Cancellation is identity-based, not granted by requests:create.

    Only the original requester or the protected technical system account may
    cancel an open request. A configurable business role/permission must not
    widen this authority.
    """
    if expense.status not in OPEN_CANCELLABLE_STATUSES:
        return False
    requester = (expense.requested_by or '').strip().lower()
    actor = (user.email or '').strip().lower()
    technical_admin = is_system_account(db, user.id) if system_admin is None else system_admin
    return requester == actor or technical_admin


@router.post('/{request_id}/cancel', response_model=ExpenseOut)
def cancel_expense(
    request_id: str,
    payload: CancellationRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    expense = db.scalar(
        select(Expense)
        .where(or_(Expense.request_id == request_id, Expense.display_id == request_id))
        .with_for_update()
    )
    if not expense:
        raise HTTPException(status_code=404, detail='Solicitud no encontrada')

    if not can_cancel_expense(db, expense, user):
        if expense.status == ExpenseStatus.CLOSED:
            raise HTTPException(status_code=409, detail='Una solicitud cerrada no puede cancelarse')
        if expense.status == ExpenseStatus.CANCELLED:
            raise HTTPException(status_code=409, detail='La solicitud ya está cancelada')
        if expense.status == ExpenseStatus.REJECTED:
            raise HTTPException(
                status_code=409,
                detail='Una solicitud rechazada debe corregirse y reenviarse, no cancelarse',
            )
        raise HTTPException(
            status_code=403,
            detail='Solo el solicitante original o el Administrador del sistema pueden cancelar una solicitud abierta',
        )

    expire_open_approvals(db, expense, actor_email=user.email)
    expense.status = ExpenseStatus.CANCELLED
    expense.cancelled_at = datetime.utcnow()
    expense.cancelled_by = user.email
    expense.cancellation_reason = payload.reason.strip()
    db.commit()

    return db.scalars(
        select(Expense)
        .where(Expense.id == expense.id)
        .options(
            selectinload(Expense.approvals),
            selectinload(Expense.attachments),
            selectinload(Expense.quotation_options),
            selectinload(Expense.quotation_votes),
        )
    ).one()
