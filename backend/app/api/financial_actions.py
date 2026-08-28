from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.security import current_user
from app.models.entities import (
    Expense,
    ExpenseAttachment,
    ExpenseStatus,
    InvoiceChangeEvent,
    User,
)
from app.schemas.expense import ExpenseOut
from app.services.closure_service import can_manage_closure, is_requester
from app.services.document_service import read_upload, write_document
from app.services.quotation_service import (
    apply_current_quotation_leader,
    can_requester_close_voting,
)

router = APIRouter()


def _expense_out(db: Session, expense_id: int) -> Expense:
    return db.scalars(
        select(Expense)
        .where(Expense.id == expense_id)
        .options(
            selectinload(Expense.approvals),
            selectinload(Expense.attachments),
            selectinload(Expense.quotation_options),
            selectinload(Expense.quotation_votes),
        )
    ).one()


def _require_closure_actor(db: Session, expense: Expense, user: User) -> None:
    if not can_manage_closure(db, expense, user):
        raise HTTPException(
            status_code=403,
            detail=(
                'Solo el solicitante original, el Administrador del sistema o un usuario '
                'delegado por el solicitante pueden registrar/corregir la factura o cerrar esta solicitud'
            ),
        )


@router.post('/{request_id}/close', response_model=ExpenseOut)
def close_expense(
    request_id: str,
    invoice: UploadFile = File(...),
    notes: str | None = Form(default=None),
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
    if expense.status not in (ExpenseStatus.APPROVED, ExpenseStatus.QUOTATION_VOTING):
        raise HTTPException(status_code=409, detail='Solo se pueden cerrar solicitudes aprobadas')
    if expense.status == ExpenseStatus.QUOTATION_VOTING:
        if not is_requester(expense, user):
            raise HTTPException(
                status_code=403,
                detail='Solo el solicitante original puede cerrar una votación al alcanzar el umbral',
            )
        if not can_requester_close_voting(db, expense, user):
            raise HTTPException(
                status_code=409,
                detail='La votación todavía no alcanza el umbral requerido con un líder único',
            )
        if apply_current_quotation_leader(db, expense) is None:
            raise HTTPException(
                status_code=409,
                detail='La votación no tiene un líder único para cerrar la solicitud',
            )
    else:
        _require_closure_actor(db, expense, user)

    content, content_type, original, stored = read_upload(invoice, label='factura')
    path = None
    try:
        path = write_document(stored, content)
        db.add(ExpenseAttachment(
            expense_id=expense.id,
            original_name=original,
            stored_name=stored,
            content_type=content_type,
            size=len(content),
            document_type='INVOICE',
        ))
        expense.status = ExpenseStatus.CLOSED
        expense.closed_at = datetime.utcnow()
        expense.closed_by = user.email
        expense.closure_notes = notes.strip() if notes else None
        db.commit()
    except Exception:
        db.rollback()
        if path and path.exists():
            path.unlink()
        raise
    return _expense_out(db, expense.id)


@router.put('/{request_id}/invoice', response_model=ExpenseOut)
def replace_invoice(
    request_id: str,
    invoice: UploadFile = File(...),
    reason: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    if len(reason.strip()) < 3:
        raise HTTPException(status_code=422, detail='Debes indicar el motivo de la corrección')
    expense = db.scalar(
        select(Expense)
        .where(or_(Expense.request_id == request_id, Expense.display_id == request_id))
        .with_for_update()
    )
    if not expense:
        raise HTTPException(status_code=404, detail='Solicitud no encontrada')
    if expense.status != ExpenseStatus.CLOSED:
        raise HTTPException(status_code=409, detail='Solo se puede corregir la factura de una solicitud cerrada')
    _require_closure_actor(db, expense, user)

    previous = db.scalar(
        select(ExpenseAttachment)
        .where(
            ExpenseAttachment.expense_id == expense.id,
            ExpenseAttachment.document_type == 'INVOICE',
        )
        .order_by(ExpenseAttachment.id.desc())
    )
    if not previous:
        raise HTTPException(status_code=409, detail='La solicitud no tiene una factura vigente para reemplazar')

    content, content_type, original, stored = read_upload(invoice, label='factura')
    path = None
    try:
        path = write_document(stored, content)
        previous.document_type = 'INVOICE_REPLACED'
        replacement = ExpenseAttachment(
            expense_id=expense.id,
            original_name=original,
            stored_name=stored,
            content_type=content_type,
            size=len(content),
            document_type='INVOICE',
        )
        db.add(replacement)
        db.flush()
        db.add(InvoiceChangeEvent(
            expense_id=expense.id,
            previous_attachment_id=previous.id,
            new_attachment_id=replacement.id,
            actor_email=user.email,
            reason=reason.strip(),
        ))
        db.commit()
    except Exception:
        db.rollback()
        if path and path.exists():
            path.unlink()
        raise
    return _expense_out(db, expense.id)
