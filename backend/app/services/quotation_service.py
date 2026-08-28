from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from fastapi import HTTPException

from app.models.entities import (
    Expense,
    ExpenseAttachment,
    ExpenseStatus,
    QuotationOption,
    QuotationVote,
    QuotationVoteEvent,
    QuotationVotingInvitation,
    User,
)
from app.services.iam_service import has_permission


def quotation_tally(db: Session, expense_id: int) -> tuple[int, int, int | None]:
    """Return frozen population, cast votes and the unique current leader."""
    invited = db.scalar(select(func.count(QuotationVotingInvitation.id)).where(
        QuotationVotingInvitation.expense_id == expense_id,
    )) or 0
    rows = db.execute(
        select(QuotationVote.quotation_option_id, func.count(QuotationVote.id))
        .where(QuotationVote.expense_id == expense_id)
        .group_by(QuotationVote.quotation_option_id)
    ).all()
    vote_count = sum(count for _, count in rows)
    if not rows:
        return invited, vote_count, None
    highest = max(count for _, count in rows)
    leaders = [option_id for option_id, count in rows if count == highest]
    return invited, vote_count, leaders[0] if len(leaders) == 1 else None


def quotation_quorum_reached(db: Session, expense: Expense) -> bool:
    required = expense.minimum_votes_required
    if required is None:
        return False
    _, vote_count, _ = quotation_tally(db, expense.id)
    return vote_count >= required


def can_vote_on_quotation(db: Session, expense: Expense, user: User) -> bool:
    if (
        expense.status != ExpenseStatus.QUOTATION_VOTING
        or not user.active
        or not has_permission(db, user.id, 'requests:approve')
    ):
        return False
    return db.scalar(select(QuotationVotingInvitation.id).where(
        QuotationVotingInvitation.expense_id == expense.id,
        QuotationVotingInvitation.voter_user_id == user.id,
    )) is not None


def can_requester_close_voting(db: Session, expense: Expense, user: User) -> bool:
    """Early invoice closure is policy-scoped and requester-only."""
    if (
        expense.status != ExpenseStatus.QUOTATION_VOTING
        or expense.request_type != 'MULTI_QUOTE'
        or expense.approval_policy_id is None
        or expense.minimum_votes_required is None
        or (expense.requested_by or '').strip().lower() != (user.email or '').strip().lower()
    ):
        return False
    _, vote_count, leader_id = quotation_tally(db, expense.id)
    return vote_count >= expense.minimum_votes_required and leader_id is not None


def apply_current_quotation_leader(db: Session, expense: Expense) -> QuotationOption | None:
    """Copy the unique current leader into the request's selected fields."""
    _, _, leader_id = quotation_tally(db, expense.id)
    if leader_id is None:
        return None
    winner = db.get(QuotationOption, leader_id)
    if not winner or winner.expense_id != expense.id:
        return None
    expense.selected_quotation_id = winner.id
    expense.supplier = winner.supplier
    expense.amount = winner.amount
    expense.item_url = winner.item_url
    return winner


def cast_quotation_vote(
    db: Session,
    expense: Expense,
    user: User,
    quotation_option_id: int,
) -> Expense:
    # Voting and invoice closure serialize on the same Expense row. The status
    # is re-read under lock so a request cannot accept a late vote after CLOSED.
    expense = db.scalar(
        select(Expense)
        .where(Expense.id == expense.id)
        .with_for_update()
        .options(
            selectinload(Expense.approvals),
            selectinload(Expense.attachments),
            selectinload(Expense.quotation_options),
            selectinload(Expense.quotation_votes),
        )
    )
    if expense.status != ExpenseStatus.QUOTATION_VOTING:
        raise HTTPException(status_code=409, detail='La votación de cotizaciones ya no está abierta')
    if not user.active or not has_permission(db, user.id, 'requests:approve'):
        raise HTTPException(status_code=403, detail='El usuario ya no tiene permiso para votar')

    invitation = db.scalar(select(QuotationVotingInvitation.id).where(
        QuotationVotingInvitation.expense_id == expense.id,
        QuotationVotingInvitation.voter_user_id == user.id,
    ))
    if not invitation:
        raise HTTPException(status_code=403, detail='Este usuario no pertenece a la población congelada de esta votación')

    supported_option_ids = set(db.scalars(select(
        ExpenseAttachment.quotation_option_id,
    ).where(
        ExpenseAttachment.expense_id == expense.id,
        ExpenseAttachment.quotation_option_id.is_not(None),
    )).all())
    unsupported = [
        item.option_number
        for item in expense.quotation_options
        if not item.item_url and item.id not in supported_option_ids
    ]
    if unsupported:
        raise HTTPException(
            status_code=409,
            detail=f'Falta soporte en las opciones: {", ".join(map(str, unsupported))}',
        )

    option = next(
        (item for item in expense.quotation_options if item.id == quotation_option_id),
        None,
    )
    if not option:
        raise HTTPException(status_code=422, detail='La cotización no pertenece a esta solicitud')

    vote = next(
        (item for item in expense.quotation_votes if item.voter_user_id == user.id),
        None,
    )
    previous = vote.quotation_option_id if vote else None
    if vote:
        vote.quotation_option_id = option.id
    else:
        vote = QuotationVote(
            expense_id=expense.id,
            quotation_option_id=option.id,
            voter_user_id=user.id,
            voter_email=user.email,
            voter_role='requests:approve',
        )
        db.add(vote)

    db.add(QuotationVoteEvent(
        expense_id=expense.id,
        flow_id=expense.flow_id,
        voter_user_id=user.id,
        voter_email=user.email,
        voter_role='requests:approve',
        previous_option_id=previous,
        selected_option_id=option.id,
    ))
    db.flush()

    invited_count, vote_count, leader_id = quotation_tally(db, expense.id)
    policy_applied = (
        expense.approval_policy_id is not None
        and expense.minimum_votes_required is not None
    )
    # A policy quorum enables requester closure but deliberately leaves voting
    # open. Without a policy, preserve the all-invited completion transition.
    if not policy_applied and invited_count and vote_count >= invited_count and leader_id is not None:
        apply_current_quotation_leader(db, expense)
        expense.status = ExpenseStatus.APPROVED
    db.commit()

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
