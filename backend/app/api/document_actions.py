from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.security import require_permission
from app.models.entities import Expense, ExpenseAttachment, QuotationOption, User
from app.schemas.expense import AttachmentOut
from app.services.approval_engine import start_approval_flow
from app.services.document_service import document_path, read_upload, write_document

router = APIRouter()


def _owned_expense(db: Session, request_id: str, user: User) -> Expense:
    expense = db.scalar(
        select(Expense)
        .where(or_(Expense.request_id == request_id, Expense.display_id == request_id))
        .options(selectinload(Expense.approvals))
    )
    if not expense:
        raise HTTPException(status_code=404, detail='Solicitud no encontrada')
    if expense.requested_by.lower() != user.email.lower():
        raise HTTPException(status_code=403, detail='Solo el solicitante puede modificar los soportes de esta solicitud')
    return expense


@router.post('/{request_id}/attachments', response_model=AttachmentOut, status_code=201)
def upload_attachment(
    request_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission('requests:create')),
):
    expense = _owned_expense(db, request_id, user)
    content, content_type, original, stored = read_upload(file, label='archivo')
    path = None
    try:
        path = write_document(stored, content)
        attachment = ExpenseAttachment(
            expense_id=expense.id,
            original_name=original,
            stored_name=stored,
            content_type=content_type,
            size=len(content),
            document_type='QUOTATION',
        )
        db.add(attachment)
        db.commit()
        db.refresh(attachment)

        if expense.request_type == 'SIMPLE' and not any(
            approval.flow_id == expense.flow_id for approval in expense.approvals
        ):
            try:
                start_approval_flow(db, expense)
            except ValueError as exc:
                db.delete(attachment)
                db.commit()
                if path.exists():
                    path.unlink()
                raise HTTPException(status_code=422, detail=str(exc)) from exc
        return attachment
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        if path and path.exists():
            path.unlink()
        raise


@router.post('/{request_id}/quotation-options/{option_id}/attachment', response_model=AttachmentOut, status_code=201)
def upload_quotation_option_attachment(
    request_id: str,
    option_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission('requests:create')),
):
    expense = _owned_expense(db, request_id, user)
    if expense.request_type != 'MULTI_QUOTE':
        raise HTTPException(status_code=409, detail='Esta solicitud no utiliza múltiples cotizaciones')
    option = db.scalar(select(QuotationOption).where(
        QuotationOption.id == option_id,
        QuotationOption.expense_id == expense.id,
    ))
    if not option:
        raise HTTPException(status_code=404, detail='Cotización no encontrada')

    content, content_type, original, stored = read_upload(file, label='cotización')
    duplicate = db.scalar(select(ExpenseAttachment.id).where(
        ExpenseAttachment.expense_id == expense.id,
        ExpenseAttachment.quotation_option_id.is_not(None),
        func.lower(ExpenseAttachment.original_name) == original.lower(),
    ))
    if duplicate:
        raise HTTPException(status_code=409, detail='Cada cotización debe usar un archivo con nombre diferente')

    path = None
    try:
        path = write_document(stored, content)
        attachment = ExpenseAttachment(
            expense_id=expense.id,
            quotation_option_id=option.id,
            original_name=original,
            stored_name=stored,
            content_type=content_type,
            size=len(content),
            document_type='QUOTATION_OPTION',
        )
        db.add(attachment)
        db.commit()
        db.refresh(attachment)
        return attachment
    except Exception:
        db.rollback()
        if path and path.exists():
            path.unlink()
        raise


@router.get('/attachments/{attachment_id}')
def download_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission('requests:read')),
):
    attachment = db.get(ExpenseAttachment, attachment_id)
    if not attachment:
        raise HTTPException(status_code=404, detail='Archivo no encontrado')
    path = document_path(attachment.stored_name)
    if not path.is_file():
        raise HTTPException(status_code=404, detail='El archivo ya no está disponible')
    return FileResponse(path, media_type=attachment.content_type, filename=attachment.original_name)
