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


def cast_quotation_vote(
    db: Session,
    expense: Expense,
    user: User,
    quotation_option_id: int,
) -> Expense:
    if expense.status != ExpenseStatus.QUOTATION_VOTING:
        raise HTTPException(status_code=409, detail='La votación de cotizaciones ya no está abierta')

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
    db.commit()

    # Invitations are the frozen participant snapshot for this voting round.
    eligible_count = db.scalar(select(func.count(QuotationVotingInvitation.id)).where(
        QuotationVotingInvitation.expense_id == expense.id,
    )) or 0
    votes = list(db.scalars(select(QuotationVote).where(
        QuotationVote.expense_id == expense.id,
    )).all())

    # Preserve the current product rule: resolution waits for every invited
    # participant and requires a unique winner. Quorum/tie policy is a separate
    # product decision and is intentionally not changed in this hardening PR.
    if eligible_count and len(votes) >= eligible_count:
        counts: dict[int, int] = {}
        for item in votes:
            counts[item.quotation_option_id] = counts.get(item.quotation_option_id, 0) + 1
        highest = max(counts.values())
        winners = [option_id for option_id, count in counts.items() if count == highest]
        if len(winners) == 1:
            winner = db.get(QuotationOption, winners[0])
            expense.selected_quotation_id = winner.id
            expense.supplier = winner.supplier
            expense.amount = winner.amount
            expense.item_url = winner.item_url
            # Legacy behavior retained intentionally for this architecture PR.
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
