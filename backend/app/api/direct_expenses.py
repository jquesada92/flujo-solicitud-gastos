import logging
import uuid
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import current_user, require_permission
from app.models.entities import ApprovalPolicy, DirectExpense, ExpenseArea, User
from app.schemas.direct_expense import DirectExpenseOut, DirectExpensePolicyOut
from app.services.approval_policy_service import (
    NO_APPROVAL_MODE,
    find_applicable_policy,
    is_no_approval_policy,
)
from app.services.document_service import document_path, read_upload, write_document
from app.services.iam_service import is_system_account


router = APIRouter()
logger = logging.getLogger(__name__)

INVOICE_SUFFIXES = {
    'application/pdf': {'.pdf'},
    'image/jpeg': {'.jpg', '.jpeg'},
    'image/png': {'.png'},
    'image/webp': {'.webp'},
}


def _clean_text(value: str, *, label: str, minimum: int, maximum: int) -> str:
    cleaned = value.strip()
    if not minimum <= len(cleaned) <= maximum:
        raise HTTPException(
            status_code=422,
            detail=f'{label} debe contener entre {minimum} y {maximum} caracteres',
        )
    return cleaned


def _validate_invoice_extension(original_name: str, content_type: str) -> None:
    suffix = Path(original_name).suffix.lower()
    if suffix not in INVOICE_SUFFIXES.get(content_type, set()):
        raise HTTPException(
            status_code=415,
            detail='La extensión de la factura no coincide con su formato declarado',
        )


def _remove_uncommitted_file(path: Path | None) -> None:
    if path is None:
        return
    try:
        path.unlink(missing_ok=True)
    except OSError:
        logger.exception('No se pudo eliminar una factura de gasto directo no confirmada')


def _present(record: DirectExpense) -> DirectExpenseOut:
    return DirectExpenseOut(
        record_id=record.record_id,
        display_id=record.display_id,
        expense_area=record.expense_area,
        supplier=record.supplier,
        item_description=record.item_description,
        amount=record.amount,
        requester_user_id=record.requester_user_id,
        requester_analytics_id=record.requester_analytics_id,
        requester_email=record.requester_email,
        approval_policy_id=record.approval_policy_id,
        invoice={
            'original_name': record.invoice_original_name,
            'content_type': record.invoice_content_type,
            'size': record.invoice_size,
            'download_url': f'/api/direct-expenses/{record.record_id}/invoice',
        },
        created_at=record.created_at,
    )


@router.get('/eligible-policies', response_model=list[DirectExpensePolicyOut])
def list_eligible_policies(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission('requests:create')),
):
    policies = db.scalars(
        select(ApprovalPolicy)
        .where(
            ApprovalPolicy.active.is_(True),
            ApprovalPolicy.approval_mode == NO_APPROVAL_MODE,
        )
        .order_by(ApprovalPolicy.expense_type, ApprovalPolicy.min_amount, ApprovalPolicy.id)
    ).all()
    return [
        DirectExpensePolicyOut(
            id=policy.id,
            name=policy.name,
            expense_area=policy.expense_type,
            min_amount=policy.min_amount,
            max_amount=policy.max_amount,
            approval_mode=policy.approval_mode,
        )
        for policy in policies
        if is_no_approval_policy(policy)
    ]


@router.post('', response_model=DirectExpenseOut, status_code=201)
def create_direct_expense(
    expense_area: str = Form(..., min_length=1, max_length=80),
    supplier: str = Form(..., min_length=2, max_length=200),
    item_description: str = Form(..., min_length=2, max_length=2000),
    amount: Decimal = Form(..., gt=0, max_digits=12, decimal_places=2),
    invoice: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission('requests:create')),
):
    area_code = _clean_text(
        expense_area,
        label='El Área',
        minimum=1,
        maximum=80,
    )
    supplier_name = _clean_text(
        supplier,
        label='El proveedor',
        minimum=2,
        maximum=200,
    )
    description = _clean_text(
        item_description,
        label='El ítem o descripción',
        minimum=2,
        maximum=2000,
    )

    active_area = db.scalar(
        select(ExpenseArea.id).where(
            ExpenseArea.code == area_code,
            ExpenseArea.active.is_(True),
        )
    )
    if active_area is None:
        raise HTTPException(status_code=422, detail='El Área no existe o está inactiva')

    try:
        policy = find_applicable_policy(db, area_code, amount)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if policy is None or not is_no_approval_policy(policy):
        raise HTTPException(
            status_code=422,
            detail='El Área y monto no coinciden con una regla activa sin aprobación',
        )

    content, content_type, original_name, stored_name = read_upload(
        invoice,
        label='factura',
    )
    _validate_invoice_extension(original_name, content_type)

    record_id = str(uuid.uuid4())
    record = DirectExpense(
        record_id=record_id,
        display_id=f'GD-{record_id}',
        expense_area=area_code,
        supplier=supplier_name,
        item_description=description,
        amount=amount,
        requester_user_id=user.id,
        requester_analytics_id=user.analytics_id,
        requester_email=user.email,
        invoice_original_name=original_name,
        invoice_stored_name=stored_name,
        invoice_content_type=content_type,
        invoice_size=len(content),
        approval_policy_id=policy.id,
    )

    path: Path | None = document_path(stored_name)
    try:
        path = write_document(stored_name, content)
        db.add(record)
        db.commit()
    except Exception:
        db.rollback()
        _remove_uncommitted_file(path)
        raise

    db.refresh(record)
    return _present(record)


@router.get('', response_model=list[DirectExpenseOut])
def list_direct_expenses(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    stmt = select(DirectExpense).order_by(
        DirectExpense.created_at.desc(),
        DirectExpense.id.desc(),
    )
    if not is_system_account(db, user.id):
        stmt = stmt.where(DirectExpense.requester_user_id == user.id)
    return [_present(record) for record in db.scalars(stmt).all()]


@router.get('/{record_id}/invoice')
def download_direct_expense_invoice(
    record_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    record = db.scalar(
        select(DirectExpense).where(DirectExpense.record_id == record_id)
    )
    if record is None:
        raise HTTPException(status_code=404, detail='Gasto directo no encontrado')
    if record.requester_user_id != user.id and not is_system_account(db, user.id):
        raise HTTPException(status_code=403, detail='No puedes acceder a esta factura')

    path = document_path(record.invoice_stored_name)
    if not path.is_file():
        raise HTTPException(status_code=404, detail='La factura ya no está disponible')
    return FileResponse(
        path,
        media_type=record.invoice_content_type,
        filename=record.invoice_original_name,
    )
