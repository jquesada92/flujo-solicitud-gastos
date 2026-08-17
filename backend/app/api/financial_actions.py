from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.api import expenses
from app.core.database import get_db
from app.core.security import require_permission
from app.models.entities import User
from app.schemas.expense import ExpenseOut

router = APIRouter()


@router.post('/{request_id}/close', response_model=ExpenseOut)
async def close_expense(
    request_id: str,
    invoice: UploadFile = File(...),
    notes: str | None = Form(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission('requests:close')),
):
    return await expenses.close_expense(
        request_id=request_id,
        invoice=invoice,
        notes=notes,
        db=db,
        user=user,
    )


@router.put('/{request_id}/invoice', response_model=ExpenseOut)
async def replace_invoice(
    request_id: str,
    invoice: UploadFile = File(...),
    reason: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission('requests:close')),
):
    return await expenses.replace_invoice(
        request_id=request_id,
        invoice=invoice,
        reason=reason,
        db=db,
        user=user,
    )
