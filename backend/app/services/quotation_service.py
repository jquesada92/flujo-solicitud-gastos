from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
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


@dataclass(frozen=True)
class QuotationVotingSummary:
    invited_count: int
    vote_count: int
    winner_option_id: int | None
    is_complete: bool
    is_tied: bool


def quotation_tracking_amount(expense: Expense) -> Decimal | None:
    """Return the operational amount shown while a quotation vote is open.

    This value is intentionally separate from ``Expense.amount``: the latter is
    the selected quotation amount and remains unset until the complete voting
    population has a unique provisional winner.
    """
    if expense.request_type != 'MULTI_QUOTE':
        return expense.amount

    options_by_id = {option.id: option for option in expense.quotation_options}
    if not options_by_id:
        return expense.amount

    maximum_amount = max(option.amount for option in options_by_id.values())
    counts: dict[int, int] = {}
    for vote in expense.quotation_votes:
        if vote.quotation_option_id in options_by_id:
            counts[vote.quotation_option_id] = counts.get(vote.quotation_option_id, 0) + 1

    if not counts:
        return maximum_amount

    highest = max(counts.values())
    leaders = [option_id for option_id, count in counts.items() if count == highest]
    if len(leaders) != 1:
        return maximum_amount
    return options_by_id[leaders[0]].amount


def quotation_voting_summary(db: Session, expense: Expense) -> QuotationVotingSummary:
    """Calculate the live result from the frozen population and active votes."""
    invited_user_ids = set(db.scalars(select(QuotationVotingInvitation.voter_user_id).where(
        QuotationVotingInvitation.expense_id == expense.id,
    )).all())
    invited_count = len(invited_user_ids)
    votes = list(db.scalars(select(QuotationVote).where(
        QuotationVote.expense_id == expense.id,
        QuotationVote.voter_user_id.in_(invited_user_ids),
    )).all()) if invited_user_ids else []
    is_complete = bool(invited_count) and len(votes) == invited_count
    if not is_complete:
        return QuotationVotingSummary(invited_count, len(votes), None, False, False)

    counts: dict[int, int] = {}
    for vote in votes:
        counts[vote.quotation_option_id] = counts.get(vote.quotation_option_id, 0) + 1
    highest = max(counts.values())
    winners = [option_id for option_id, count in counts.items() if count == highest]
    return QuotationVotingSummary(
        invited_count=invited_count,
        vote_count=len(votes),
        winner_option_id=winners[0] if len(winners) == 1 else None,
        is_complete=True,
        is_tied=len(winners) != 1,
    )


def refresh_provisional_winner(db: Session, expense: Expense) -> QuotationVotingSummary:
    """Keep the provisional winner synchronized without closing the voting round."""
    summary = quotation_voting_summary(db, expense)
    if summary.winner_option_id is None:
        expense.selected_quotation_id = None
        expense.supplier = None
        expense.amount = None
        expense.item_url = None
        return summary

    winner = db.get(QuotationOption, summary.winner_option_id)
    if winner is None:
        raise HTTPException(status_code=409, detail='La cotización ganadora ya no está disponible')
    expense.selected_quotation_id = winner.id
    expense.supplier = winner.supplier
    expense.amount = winner.amount
    expense.item_url = winner.item_url
    return summary


def require_unique_winner_for_closure(db: Session, expense: Expense) -> QuotationVotingSummary:
    """Reject invoice closure until everybody voted and one option leads alone."""
    summary = refresh_provisional_winner(db, expense)
    if not summary.is_complete:
        raise HTTPException(
            status_code=409,
            detail='La votación sigue abierta hasta que todos los participantes registren su voto',
        )
    if summary.is_tied:
        raise HTTPException(
            status_code=409,
            detail='La votación está empatada. Un aprobador debe cambiar su voto antes de registrar la factura',
        )
    return summary


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
    db.flush()
    refresh_provisional_winner(db, expense)
    # A unique leader is provisional. The round remains open so invited users
    # may change their vote; uploading the invoice is the closing event.
    expense.status = ExpenseStatus.QUOTATION_VOTING
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
