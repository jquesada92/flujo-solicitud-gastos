import os
import secrets
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import or_, select, text
from sqlalchemy.orm import Session, selectinload
from app.core.database import get_db
from app.core.security import current_user, require_permission, require_roles
from app.models.entities import Expense, ExpenseAttachment, ExpenseStatus, User, UserRole
from app.schemas.expense import AttachmentOut, ExpenseCreate, ExpenseOut, InvoiceOut
from app.services.approval_engine import expire_open_approvals, start_approval_flow

router = APIRouter()
UPLOAD_DIR = Path(os.getenv('UPLOAD_DIR', '/app/uploads'))
MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_TYPES = {'application/pdf', 'image/jpeg', 'image/png', 'image/webp'}
DISPLAY_PREFIXES = {
    'ADMINISTRATION': 'ADM', 'MAINTENANCE': 'MAN', 'EXTRAORDINARY': 'EXT',
    'LEGAL': 'LEG', 'POOL': 'PIS', 'GYM': 'GYM', 'SQUASH_COURT': 'SQU',
}


def _next_display_id(db: Session, category: str) -> str:
    year = datetime.utcnow().year
    counter_key = f'{category}:{year}'
    value = db.execute(
        text('''INSERT INTO category_counters (category, last_value) VALUES (:category, 1)
                ON CONFLICT (category) DO UPDATE SET last_value = category_counters.last_value + 1
                RETURNING last_value'''),
        {'category': counter_key},
    ).scalar_one()
    prefix = DISPLAY_PREFIXES.get(category, category[:3].upper()).ljust(3, 'X')[:3]
    return f'{prefix}-{year}-{value:011d}'


class CancellationRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


@router.get('', response_model=list[ExpenseOut])
def list_expenses(db: Session = Depends(get_db), user: User = Depends(current_user)):
    if user.role != UserRole.ADMIN and not user.can_view:
        raise HTTPException(status_code=403, detail='No tienes permiso para consultar solicitudes')
    stmt = select(Expense).options(selectinload(Expense.approvals), selectinload(Expense.attachments)).order_by(Expense.id.desc())
    if user.role == UserRole.REQUESTER:
        stmt = stmt.where(Expense.requested_by == user.email)
    return list(db.scalars(stmt).all())


@router.get('/invoices', response_model=list[InvoiceOut])
def list_invoices(
    q: str | None = Query(default=None, max_length=200),
    category: str | None = Query(default=None, max_length=80),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    if user.role != UserRole.ADMIN and not user.can_view:
        raise HTTPException(status_code=403, detail='No tienes permiso para consultar facturas')

    stmt = (
        select(ExpenseAttachment, Expense)
        .join(Expense, Expense.id == ExpenseAttachment.expense_id)
        .where(ExpenseAttachment.document_type == 'INVOICE')
        .order_by(ExpenseAttachment.created_at.desc(), ExpenseAttachment.id.desc())
    )
    if user.role == UserRole.REQUESTER:
        stmt = stmt.where(Expense.requested_by == user.email)
    if category:
        stmt = stmt.where(Expense.expense_type == category)
    if q and q.strip():
        term = f'%{q.strip()}%'
        stmt = stmt.where(or_(
            ExpenseAttachment.original_name.ilike(term),
            Expense.display_id.ilike(term),
            Expense.request_id.ilike(term),
            Expense.flow_id.ilike(term),
            Expense.title.ilike(term),
            Expense.supplier.ilike(term),
            Expense.requested_by.ilike(term),
        ))

    return [
        InvoiceOut(
            attachment_id=attachment.id,
            original_name=attachment.original_name,
            content_type=attachment.content_type,
            size=attachment.size,
            uploaded_at=attachment.created_at,
            request_id=expense.request_id,
            display_id=expense.display_id,
            flow_id=expense.flow_id,
            title=expense.title,
            expense_type=expense.expense_type,
            expense_subcategory=expense.expense_subcategory,
            supplier=expense.supplier,
            amount=expense.amount,
            requested_by=expense.requested_by,
            expense_status=expense.status.value,
            closed_at=expense.closed_at,
            closed_by=expense.closed_by,
        )
        for attachment, expense in db.execute(stmt).all()
    ]


@router.post('', response_model=ExpenseOut, status_code=201)
def create_expense(
    payload: ExpenseCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission('can_request')),
):
    quotation_pending = payload.quotation_pending
    values = payload.model_dump(mode='json', exclude={'quotation_pending'})
    revised_from = values.get('revised_from_request_id')
    source = None
    if revised_from:
        raise HTTPException(
            status_code=409,
            detail='Esta pantalla de corrección está desactualizada. Recarga la aplicación y usa nuevamente “Corregir / reenviar”.',
        )
    expense = Expense(**values, requested_by=user.email, display_id=_next_display_id(db, payload.expense_type))
    if source:
        expire_open_approvals(db, source, actor_email=user.email)
        if source.status in (ExpenseStatus.SUBMITTED, ExpenseStatus.PENDING_APPROVAL, ExpenseStatus.APPROVED):
            source.status = ExpenseStatus.CANCELLED
            source.cancelled_at = datetime.utcnow()
            source.cancelled_by = user.email
            source.cancellation_reason = 'Flujo reemplazado por una solicitud corregida'
    db.add(expense)
    db.commit()
    db.refresh(expense)

    if not quotation_pending:
        try:
            start_approval_flow(db, expense)
        except ValueError as exc:
            db.delete(expense)
            db.commit()
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    stmt = select(Expense).where(Expense.id == expense.id).options(selectinload(Expense.approvals), selectinload(Expense.attachments))
    return db.scalars(stmt).one()


@router.put('/{request_id}/resubmit', response_model=ExpenseOut)
def resubmit_expense(
    request_id: str,
    payload: ExpenseCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission('can_request')),
):
    expense = _expense_for_user(db, request_id, user)
    db.scalar(select(Expense).where(Expense.id == expense.id).with_for_update())
    db.refresh(expense)
    if expense.status == ExpenseStatus.CLOSED:
        raise HTTPException(status_code=409, detail='Una solicitud cerrada no puede corregirse')

    expire_open_approvals(db, expense, actor_email=user.email)
    values = payload.model_dump(mode='json', exclude={'quotation_pending', 'revised_from_request_id'})
    for field, value in values.items():
        setattr(expense, field, value)
    expense.flow_id = str(uuid.uuid4())
    expense.status = ExpenseStatus.SUBMITTED
    expense.cancelled_at = None
    expense.cancelled_by = None
    expense.cancellation_reason = None
    db.commit()
    db.refresh(expense)

    if not payload.quotation_pending:
        try:
            start_approval_flow(db, expense)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    stmt = select(Expense).where(Expense.id == expense.id).options(selectinload(Expense.approvals), selectinload(Expense.attachments))
    return db.scalars(stmt).one()


def _expense_for_user(db: Session, request_id: str, user: User) -> Expense:
    expense = db.scalar(select(Expense).where(or_(Expense.request_id == request_id, Expense.display_id == request_id)))
    if not expense:
        raise HTTPException(status_code=404, detail='Solicitud no encontrada')
    if user.role == UserRole.REQUESTER and expense.requested_by != user.email:
        raise HTTPException(status_code=403, detail='No tienes acceso a esta solicitud')
    return expense


@router.post('/{request_id}/attachments', response_model=AttachmentOut, status_code=201)
async def upload_attachment(
    request_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission('can_request')),
):
    expense = _expense_for_user(db, request_id, user)
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail='Solo se permiten archivos PDF, JPG, PNG o WEBP')
    content = await file.read(MAX_FILE_SIZE + 1)
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail='El archivo supera el límite de 10 MB')
    safe_original = Path(file.filename or 'cotizacion').name[:255]
    suffix = Path(safe_original).suffix.lower()
    stored_name = f'{secrets.token_hex(20)}{suffix}'
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    (UPLOAD_DIR / stored_name).write_bytes(content)
    attachment = ExpenseAttachment(expense_id=expense.id, original_name=safe_original, stored_name=stored_name, content_type=file.content_type, size=len(content))
    db.add(attachment); db.commit(); db.refresh(attachment)
    if not any(approval.flow_id == expense.flow_id for approval in expense.approvals):
        try:
            start_approval_flow(db, expense)
        except ValueError as exc:
            db.delete(attachment)
            db.commit()
            path = UPLOAD_DIR / stored_name
            if path.exists():
                path.unlink()
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    return attachment


@router.get('/attachments/{attachment_id}')
def download_attachment(attachment_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    attachment = db.scalar(select(ExpenseAttachment).where(ExpenseAttachment.id == attachment_id).options(selectinload(ExpenseAttachment.expense)))
    if not attachment:
        raise HTTPException(status_code=404, detail='Archivo no encontrado')
    if user.role == UserRole.REQUESTER and attachment.expense.requested_by != user.email:
        raise HTTPException(status_code=403, detail='No tienes acceso a este archivo')
    path = UPLOAD_DIR / attachment.stored_name
    if not path.is_file():
        raise HTTPException(status_code=404, detail='El archivo ya no está disponible')
    return FileResponse(path, media_type=attachment.content_type, filename=attachment.original_name)


@router.post('/{request_id}/cancel', response_model=ExpenseOut)
def cancel_expense(request_id: str, payload: CancellationRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    expense = _expense_for_user(db, request_id, user)
    db.scalar(select(Expense).where(Expense.id == expense.id).with_for_update())
    db.refresh(expense)
    if user.role != UserRole.ADMIN and not user.can_request:
        raise HTTPException(status_code=403, detail='No tienes permiso para cancelar solicitudes')
    if expense.status == ExpenseStatus.CLOSED:
        raise HTTPException(status_code=409, detail='Una solicitud cerrada no puede cancelarse')
    if expense.status == ExpenseStatus.CANCELLED:
        raise HTTPException(status_code=409, detail='La solicitud ya está cancelada')
    if expense.status == ExpenseStatus.REJECTED:
        raise HTTPException(status_code=409, detail='Una solicitud rechazada debe corregirse y reenviarse, no cancelarse')
    expense.status = ExpenseStatus.CANCELLED
    expire_open_approvals(db, expense, actor_email=user.email)
    expense.cancelled_at = datetime.utcnow()
    expense.cancelled_by = user.email
    expense.cancellation_reason = payload.reason.strip()
    db.commit()
    stmt = select(Expense).where(Expense.id == expense.id).options(selectinload(Expense.approvals), selectinload(Expense.attachments))
    return db.scalars(stmt).one()


@router.post('/{request_id}/close', response_model=ExpenseOut)
async def close_expense(
    request_id: str,
    invoice: UploadFile = File(...),
    notes: str | None = Form(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN)),
):
    expense = _expense_for_user(db, request_id, user)
    if expense.status != ExpenseStatus.APPROVED:
        raise HTTPException(status_code=409, detail='Solo se pueden cerrar solicitudes aprobadas')
    documents = [('INVOICE', invoice)]
    prepared = []
    for document_type, upload in documents:
        if upload.content_type not in ALLOWED_TYPES:
            raise HTTPException(status_code=415, detail='La factura debe ser un archivo PDF, JPG, PNG o WEBP')
        content = await upload.read(MAX_FILE_SIZE + 1)
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail='Cada archivo debe pesar máximo 10 MB')
        original = Path(upload.filename or document_type.lower()).name[:255]
        stored = f'{secrets.token_hex(20)}{Path(original).suffix.lower()}'
        prepared.append((document_type, upload.content_type, original, stored, content))
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    written = []
    try:
        for document_type, content_type, original, stored, content in prepared:
            path = UPLOAD_DIR / stored; path.write_bytes(content); written.append(path)
            db.add(ExpenseAttachment(expense_id=expense.id, original_name=original, stored_name=stored, content_type=content_type, size=len(content), document_type=document_type))
        expense.status = ExpenseStatus.CLOSED
        expense.closed_at = datetime.utcnow()
        expense.closed_by = user.email
        expense.closure_notes = notes.strip() if notes else None
        db.commit()
    except Exception:
        db.rollback()
        for path in written:
            if path.exists(): path.unlink()
        raise
    stmt = select(Expense).where(Expense.id == expense.id).options(selectinload(Expense.approvals), selectinload(Expense.attachments))
    return db.scalars(stmt).one()
