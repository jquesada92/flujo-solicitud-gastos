from collections import defaultdict

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.orm import Session

from app.models.closure import ExpenseClosureDelegation
from app.models.entities import (
    Approval,
    ApprovalStatus,
    Expense,
    ExpenseStatus,
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
    Approval/voting require both IAM permission and workflow assignment. Closure
    is different: it is a per-request responsibility of the requester or their
    active delegate, not a generic ``requests:close`` entitlement.
    """
    scoped_ids = None if expense_ids is None else list(dict.fromkeys(expense_ids))
    if scoped_ids == []:
        return {}

    actions: dict[int, list[str]] = defaultdict(list)

    if has_permission(db, user.id, 'requests:approve'):
        approvals = (
            select(Approval.expense_id)
            .join(Expense, Expense.id == Approval.expense_id)
            .where(
                func.lower(Approval.approver_email) == user.email.lower(),
                Approval.status == ApprovalStatus.PENDING,
                Expense.status == ExpenseStatus.PENDING_APPROVAL,
            )
            .distinct()
        )
        if scoped_ids is not None:
            approvals = approvals.where(Approval.expense_id.in_(scoped_ids))
        for expense_id in db.scalars(approvals).all():
            _append(actions, expense_id, APPROVAL_DECISION)

        quotation_votes = (
            select(QuotationVotingInvitation.expense_id)
            .join(Expense, Expense.id == QuotationVotingInvitation.expense_id)
            .where(
                QuotationVotingInvitation.voter_user_id == user.id,
                Expense.status == ExpenseStatus.QUOTATION_VOTING,
            )
            .distinct()
        )
        if scoped_ids is not None:
            quotation_votes = quotation_votes.where(
                QuotationVotingInvitation.expense_id.in_(scoped_ids)
            )
        for expense_id in db.scalars(quotation_votes).all():
            _append(actions, expense_id, QUOTATION_VOTE)

    # A revision request creates a task for the original requester. It is not a
    # generic requests:create task for every creator-capable user. The protected
    # system administrator can still correct from the request list as a resource
    # capability, but the personal dashboard task belongs to the requester.
    corrections = select(Expense.id).where(
        Expense.status == ExpenseStatus.NEEDS_REVISION,
        func.lower(Expense.requested_by) == user.email.lower(),
    )
    if scoped_ids is not None:
        corrections = corrections.where(Expense.id.in_(scoped_ids))
    for expense_id in db.scalars(corrections).all():
        _append(actions, expense_id, CORRECT_REQUEST)

    # Closing an approved request belongs to its original requester or to the
    # current active delegate explicitly chosen by that requester. The technical
    # administrator can execute closure as an administrative exception from the
    # request list, but does not receive every organization's closure as a task.
    delegated_expense = exists(
        select(ExpenseClosureDelegation.id).where(
            ExpenseClosureDelegation.expense_id == Expense.id,
            ExpenseClosureDelegation.delegate_user_id == user.id,
            ExpenseClosureDelegation.revoked_at.is_(None),
        )
    )
    closures = select(Expense.id).where(
        or_(
            and_(
                Expense.request_type != 'MULTI_QUOTE',
                Expense.status == ExpenseStatus.APPROVED,
            ),
            and_(
                Expense.request_type == 'MULTI_QUOTE',
                Expense.status == ExpenseStatus.QUOTATION_VOTING,
                Expense.selected_quotation_id.is_not(None),
            ),
        ),
        or_(
            func.lower(Expense.requested_by) == user.email.lower(),
            delegated_expense,
        ),
    )
    if scoped_ids is not None:
        closures = closures.where(Expense.id.in_(scoped_ids))
    for expense_id in db.scalars(closures).all():
        _append(actions, expense_id, CLOSE_REQUEST)

    return {
        expense_id: sorted(codes, key=ACTION_ORDER.index)
        for expense_id, codes in actions.items()
        if codes
    }
