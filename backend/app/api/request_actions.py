import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.expenses import _next_display_id, _validate_area_selection
from app.core.database import get_db
from app.core.security import require_permission
from app.models.entities import (
    Expense,
    ExpenseStatus,
    QuotationOption,
    QuotationVotingInvitation,
    User,
)
from app.schemas.expense import ExpenseCreate, ExpenseOut
from app.services.approval_engine import start_approval_flow
from app.services.email_service import send_quotation_vote_request
from app.services.iam_service import users_with_permission

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post('', response_model=ExpenseOut, status_code=201)
def create_expense(
    payload: ExpenseCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission('requests:create')),
):
    """Create a request without consulting legacy role/can_* fields."""
    _validate_area_selection(db, payload.expense_type, payload.expense_subcategory)
    if payload.revised_from_request_id:
        raise HTTPException(
            status_code=409,
            detail='Usa la acción de corregir y reenviar para modificar una solicitud existente',
        )

    quotation_pending = payload.quotation_pending
    quote_values = payload.quotation_options
    values = payload.model_dump(
        mode='json',
        exclude={'quotation_pending', 'quotation_options'},
    )
    expense = Expense(
        **values,
        requested_by=user.email,
        requester_analytics_id=user.analytics_id,
        display_id=_next_display_id(db, payload.expense_type),
    )
    if payload.request_type == 'MULTI_QUOTE':
        expense.status = ExpenseStatus.QUOTATION_VOTING

    db.add(expense)
    db.flush()

    if payload.request_type == 'MULTI_QUOTE':
        db.add_all([
            QuotationOption(
                expense_id=expense.id,
                option_number=index,
                supplier=option.supplier,
                amount=option.amount,
                item_url=str(option.item_url) if option.item_url else None,
                notes=option.notes,
            )
            for index, option in enumerate(quote_values, 1)
        ])
        db.flush()

        voters = users_with_permission(
            db,
            'requests:approve',
            exclude_email=user.email.lower(),
        )
        if not voters:
            db.rollback()
            raise HTTPException(
                status_code=422,
                detail='No existe otro usuario activo con permiso de aprobación para participar en la votación',
            )
        invitations: list[tuple[User, QuotationVotingInvitation]] = []
        for voter in voters:
            invitation = QuotationVotingInvitation(
                expense_id=expense.id,
                voter_user_id=voter.id,
            )
            db.add(invitation)
            db.flush()
            invitations.append((voter, invitation))
        db.commit()

        expense = db.scalar(
            select(Expense)
            .where(Expense.id == expense.id)
            .options(
                selectinload(Expense.approvals),
                selectinload(Expense.attachments),
                selectinload(Expense.quotation_options),
                selectinload(Expense.quotation_votes),
            )
        )
        for voter, invitation in invitations:
            try:
                send_quotation_vote_request(expense, voter, invitation)
            except Exception:
                logger.exception('Quotation voting email delivery failed; request remains saved')
        return expense

    db.commit()
    db.refresh(expense)
    if not quotation_pending:
        try:
            start_approval_flow(db, expense)
        except ValueError as exc:
            db.delete(expense)
            db.commit()
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    stmt = (
        select(Expense)
        .where(Expense.id == expense.id)
        .options(
            selectinload(Expense.approvals),
            selectinload(Expense.attachments),
            selectinload(Expense.quotation_options),
            selectinload(Expense.quotation_votes),
        )
    )
    return db.scalars(stmt).one()
