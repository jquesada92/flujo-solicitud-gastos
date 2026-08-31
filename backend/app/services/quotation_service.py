from dataclasses import dataclass
from decimal import Decimal

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
    invited_user_ids = set(db.scalars(
        select(QuotationVotingInvitation.voter_user_id).where(
            QuotationVotingInvitation.expense_id == expense_id,
        )
    ).all())
    invited = len(invited_user_ids)
    if not invited_user_ids:
        return 0, 0, None

    rows = db.execute(
        select(QuotationVote.quotation_option_id, func.count(QuotationVote.id))
        .join(QuotationOption, QuotationOption.id == QuotationVote.quotation_option_id)
        .where(
            QuotationVote.expense_id == expense_id,
            QuotationVote.voter_user_id.in_(invited_user_ids),
            QuotationOption.expense_id == expense_id,
        )
        .group_by(QuotationVote.quotation_option_id)
    ).all()
    vote_count = sum(count for _, count in rows)
    if not rows:
        return invited, vote_count, None
    highest = max(count for _, count in rows)
    leaders = [option_id for option_id, count in rows if count == highest]
    return invited, vote_count, leaders[0] if len(leaders) == 1 else None


def quotation_quorum_reached(db: Session, expense: Expense) -> bool:
    return quotation_voting_summary(db, expense).quorum_reached


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
    summary = quotation_voting_summary(db, expense)
    return summary.quorum_reached and summary.winner_option_id is not None


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


@dataclass(frozen=True)
class QuotationVotingSummary:
    invited_count: int
    vote_count: int
    minimum_votes_required: int
    winner_option_id: int | None
    quorum_reached: bool
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
    """Calculate the live result using the round's frozen population and threshold."""
    invited_count, vote_count, leader_id = quotation_tally(db, expense.id)
    if expense.approval_policy_id is not None and expense.minimum_votes_required is not None:
        minimum_votes_required = expense.minimum_votes_required
    else:
        # The IAM fallback is not an early close: every frozen participant must
        # vote before a provisional winner can be invoiced.
        minimum_votes_required = invited_count
    quorum_reached = (
        invited_count > 0
        and minimum_votes_required > 0
        and vote_count >= minimum_votes_required
    )
    return QuotationVotingSummary(
        invited_count=invited_count,
        vote_count=vote_count,
        minimum_votes_required=minimum_votes_required,
        winner_option_id=leader_id if quorum_reached else None,
        quorum_reached=quorum_reached,
        is_complete=bool(invited_count) and vote_count >= invited_count,
        is_tied=quorum_reached and leader_id is None,
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
    """Reject closure until the configured threshold (or full fallback) has one leader."""
    summary = refresh_provisional_winner(db, expense)
    if not summary.quorum_reached:
        detail = (
            'La votación todavía no alcanza el umbral requerido'
            if expense.approval_policy_id is not None
            else 'La votación sigue abierta hasta que todos los participantes registren su voto'
        )
        raise HTTPException(
            status_code=409,
            detail=detail,
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
    refresh_provisional_winner(db, expense)
    # Any unique leader remains provisional. Policy rounds can close at their
    # frozen threshold; the IAM fallback waits for the whole frozen population.
    # In both cases invited users may change their vote until invoice + CLOSED.
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
