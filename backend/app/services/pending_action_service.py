from collections import defaultdict

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from app.models.entities import (
    Approval,
    ApprovalStatus,
    Expense,
    ExpenseStatus,
    QuotationVote,
    QuotationVotingInvitation,
    User,
)
from app.services.iam_service import has_permission


APPROVAL_DECISION = 'APPROVAL_DECISION'
QUOTATION_VOTE = 'QUOTATION_VOTE'
CORRECT_REQUEST = 'CORRECT_REQUEST'
CLOSE_REQUEST = 'CLOSE_REQUEST'

ACTION_ORDER = (
    APPROVAL_DECISION,
    QUOTATION_VOTE,
    CORRECT_REQUEST,
    CLOSE_REQUEST,
)


def _append(actions: dict[int, list[str]], expense_id: int, code: str) -> None:
    if code not in actions[expense_id]:
        actions[expense_id].append(code)


def pending_actions_by_expense(
    db: Session,
    user: User,
    *,
    expense_ids: list[int] | set[int] | tuple[int, ...] | None = None,
) -> dict[int, list[str]]:
    """Resolve the mutable workflow actions currently assigned to one user.

    This is the backend source of truth for Dashboard -> Acciones pendientes.
    It intentionally resolves concrete workflow assignments in addition to IAM:
    a user may have ``requests:approve`` without having a pending approval or
    quotation invitation for a particular request.
    """
    scoped_ids = None if expense_ids is None else list(dict.fromkeys(expense_ids))
    if scoped_ids == []:
        return {}

    actions: dict[int, list[str]] = defaultdict(list)

    if has_permission(db, user.id, 'requests:approve'):
        approvals = select(Approval.expense_id).where(
            func.lower(Approval.approver_email) == user.email.lower(),
            Approval.status == ApprovalStatus.PENDING,
        )
        if scoped_ids is not None:
            approvals = approvals.where(Approval.expense_id.in_(scoped_ids))
        for expense_id in db.scalars(approvals).all():
            _append(actions, expense_id, APPROVAL_DECISION)

        already_voted = exists(
            select(QuotationVote.id).where(
                QuotationVote.expense_id == QuotationVotingInvitation.expense_id,
                QuotationVote.voter_user_id == user.id,
            )
        )
        quotation_votes = (
            select(QuotationVotingInvitation.expense_id)
            .join(Expense, Expense.id == QuotationVotingInvitation.expense_id)
            .where(
                QuotationVotingInvitation.voter_user_id == user.id,
                Expense.status == ExpenseStatus.QUOTATION_VOTING,
                ~already_voted,
            )
            .distinct()
        )
        if scoped_ids is not None:
            quotation_votes = quotation_votes.where(
                QuotationVotingInvitation.expense_id.in_(scoped_ids)
            )
        for expense_id in db.scalars(quotation_votes).all():
            _append(actions, expense_id, QUOTATION_VOTE)

    if has_permission(db, user.id, 'requests:create'):
        corrections = select(Expense.id).where(
            Expense.status == ExpenseStatus.NEEDS_REVISION,
            func.lower(Expense.requested_by) == user.email.lower(),
        )
        if scoped_ids is not None:
            corrections = corrections.where(Expense.id.in_(scoped_ids))
        for expense_id in db.scalars(corrections).all():
            _append(actions, expense_id, CORRECT_REQUEST)

    if has_permission(db, user.id, 'requests:close'):
        closures = select(Expense.id).where(Expense.status == ExpenseStatus.APPROVED)
        if scoped_ids is not None:
            closures = closures.where(Expense.id.in_(scoped_ids))
        for expense_id in db.scalars(closures).all():
            _append(actions, expense_id, CLOSE_REQUEST)

    return {
        expense_id: sorted(codes, key=ACTION_ORDER.index)
        for expense_id, codes in actions.items()
        if codes
    }
