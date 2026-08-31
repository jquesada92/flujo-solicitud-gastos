from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.security import require_permission
from app.models.entities import Expense, QuotationVotingInvitation, User
from app.schemas.expense import ExpenseOut
from app.schemas.quotation import QuotationVoteRequest
from app.services.iam_service import has_permission
from app.services.quotation_service import cast_quotation_vote

router = APIRouter()


@router.post('/{request_id}/quotation-vote', response_model=ExpenseOut)
def vote_quotation(
    request_id: str,
    payload: QuotationVoteRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission('requests:approve')),
):
    expense = db.scalar(
        select(Expense)
        .where(or_(Expense.request_id == request_id, Expense.display_id == request_id))
        .with_for_update()
        .options(
            selectinload(Expense.quotation_options),
            selectinload(Expense.quotation_votes),
            selectinload(Expense.approvals),
            selectinload(Expense.attachments),
        )
    )
    if not expense:
        raise HTTPException(status_code=404, detail='Solicitud no encontrada')
    return cast_quotation_vote(db, expense, user, payload.quotation_option_id)


@router.post('/quotation-vote-email/{token}')
def decide_email_quotation_vote(
    token: str,
    payload: QuotationVoteRequest,
    db: Session = Depends(get_db),
):
    invitation = db.scalar(select(QuotationVotingInvitation).where(
        QuotationVotingInvitation.token == token,
    ))
    if not invitation:
        raise HTTPException(status_code=404, detail='Invitación de votación no encontrada')
    user = db.get(User, invitation.voter_user_id)
    if not user or not user.active or not has_permission(db, user.id, 'requests:approve'):
        raise HTTPException(status_code=403, detail='El usuario delegado para votar ya no está habilitado')
    expense = db.scalar(
        select(Expense)
        .where(Expense.id == invitation.expense_id)
        .with_for_update()
        .options(
            selectinload(Expense.quotation_options),
            selectinload(Expense.quotation_votes),
            selectinload(Expense.approvals),
            selectinload(Expense.attachments),
        )
    )
    result = cast_quotation_vote(db, expense, user, payload.quotation_option_id)
    return {
        'status': result.status.value,
        'display_id': result.display_id,
        'quotation_option_id': payload.quotation_option_id,
    }
