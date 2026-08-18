from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.cancellation_actions import can_cancel_expense
from app.api.expenses import APP_TIME_ZONE, _as_utc, _present_expense, _user_names
from app.api.revision_actions import can_correct_expense
from app.core.database import get_db
from app.core.security import require_permission
from app.models.entities import (
    ApprovalStepEvent,
    Expense,
    ExpenseAttachment,
    ExpenseStatus,
    QuotationVotingInvitation,
    User,
)
from app.schemas.expense import ExpenseOut
from app.services.closure_service import can_delegate_closure, can_manage_closure
from app.services.iam_service import is_system_account
from app.services.pending_action_service import pending_actions_by_expense

router = APIRouter()


@router.get('', response_model=list[ExpenseOut])
def list_trackable_expenses(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission('requests:read')),
):
    """Return the shared request-tracking view for every active user.

    Read access is a product baseline. Organizational roles or requester identity
    must not reduce the set of requests visible for follow-up. Mutating
    capabilities are calculated per request and remain backend-authoritative.
    """
    open_statuses = (
        ExpenseStatus.SUBMITTED,
        ExpenseStatus.PENDING_APPROVAL,
        ExpenseStatus.APPROVED,
        ExpenseStatus.NEEDS_REVISION,
        ExpenseStatus.QUOTATION_VOTING,
        ExpenseStatus.REJECTED,
    )
    recent_closed_threshold = datetime.utcnow() - timedelta(days=7)
    has_invoice = exists(select(ExpenseAttachment.id).where(
        ExpenseAttachment.expense_id == Expense.id,
        ExpenseAttachment.document_type == 'INVOICE',
    ))
    stmt = (
        select(Expense)
        .where(or_(
            Expense.status.in_(open_statuses),
            and_(
                Expense.status == ExpenseStatus.CLOSED,
                Expense.closed_at >= recent_closed_threshold,
                has_invoice,
            ),
        ))
        .options(
            selectinload(Expense.approvals),
            selectinload(Expense.attachments),
            selectinload(Expense.quotation_options),
            selectinload(Expense.quotation_votes),
        )
        .order_by(Expense.id.desc())
    )

    names = _user_names(db)
    expenses = list(db.scalars(stmt).all())
    expense_ids = [expense.id for expense in expenses]
    latest_events: dict[int, ApprovalStepEvent] = {}
    quotation_voter_counts: dict[int, int] = {}
    system_admin = is_system_account(db, user.id)

    if expense_ids:
        events = db.scalars(
            select(ApprovalStepEvent)
            .where(ApprovalStepEvent.expense_id.in_(expense_ids))
            .order_by(
                ApprovalStepEvent.expense_id,
                ApprovalStepEvent.occurred_at.desc(),
                ApprovalStepEvent.event_sequence.desc(),
            )
        ).all()
        for event in events:
            latest_events.setdefault(event.expense_id, event)

        quotation_voter_counts = dict(db.execute(
            select(
                QuotationVotingInvitation.expense_id,
                func.count(QuotationVotingInvitation.id),
            )
            .where(QuotationVotingInvitation.expense_id.in_(expense_ids))
            .group_by(QuotationVotingInvitation.expense_id)
        ).all())

    output: list[ExpenseOut] = []
    for expense in expenses:
        event = latest_events.get(expense.id)
        lifecycle = [
            (expense.closed_at, 'REQUEST_CLOSED'),
            (expense.cancelled_at, 'REQUEST_CANCELLED'),
        ]
        lifecycle_at, lifecycle_type = max(
            ((at, kind) for at, kind in lifecycle if at),
            default=(None, None),
            key=lambda item: item[0],
        )
        presented = _present_expense(
            expense,
            names,
            event,
            quotation_voter_counts.get(expense.id, 0),
        ).model_copy(update={
            'can_cancel': can_cancel_expense(
                db,
                expense,
                user,
                system_admin=system_admin,
            ),
            'can_correct': can_correct_expense(
                db,
                expense,
                user,
                system_admin=system_admin,
            ),
            'can_close': can_manage_closure(
                db,
                expense,
                user,
                system_admin=system_admin,
            ),
            'can_delegate_close': can_delegate_closure(expense, user),
        })
        if lifecycle_at and (
            not event or lifecycle_at.replace(tzinfo=None) > event.occurred_at.replace(tzinfo=None)
        ):
            presented = presented.model_copy(update={
                'last_event_at': _as_utc(lifecycle_at),
                'last_event_type': lifecycle_type,
            })
        if presented.last_event_at and presented.last_event_at < presented.created_at:
            presented = presented.model_copy(update={
                'last_event_at': presented.created_at,
                'last_event_type': 'REQUEST_CREATED',
            })
        output.append(presented)

    return output


@router.get('/dashboard')
def expense_dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission('requests:read')),
):
    """Shared dashboard plus user-specific actionable work."""
    now_local = datetime.now(ZoneInfo(APP_TIME_ZONE))
    now_utc = now_local.astimezone(timezone.utc).replace(tzinfo=None)
    period_start_utc = (now_local - timedelta(days=30)).replace(
        hour=0, minute=0, second=0, microsecond=0,
    ).astimezone(timezone.utc).replace(tzinfo=None)

    open_statuses = [
        ExpenseStatus.QUOTATION_VOTING,
        ExpenseStatus.SUBMITTED,
        ExpenseStatus.PENDING_APPROVAL,
        ExpenseStatus.APPROVED,
        ExpenseStatus.NEEDS_REVISION,
    ]
    in_process = db.scalar(
        select(func.count(Expense.id)).where(Expense.status.in_(open_statuses))
    ) or 0
    closed_24h = db.scalar(
        select(func.count(Expense.id)).where(
            Expense.status == ExpenseStatus.CLOSED,
            Expense.closed_at >= now_utc - timedelta(hours=24),
        )
    ) or 0

    action_map = pending_actions_by_expense(db, user)
    pending_ids = set(action_map)
    pending_items = (
        list(db.scalars(
            select(Expense)
            .where(Expense.id.in_(pending_ids))
            .order_by(Expense.created_at.asc())
            .limit(8)
        ).all())
        if pending_ids else []
    )

    month_rows = db.execute(
        select(Expense.status, func.count(Expense.id))
        .where(Expense.created_at >= period_start_utc)
        .group_by(Expense.status)
    ).all()
    month_by_status = {status.value: count for status, count in month_rows}
    month_amount = db.scalar(
        select(func.coalesce(func.sum(Expense.amount), 0)).where(
            Expense.created_at >= period_start_utc,
            Expense.status.in_([ExpenseStatus.APPROVED, ExpenseStatus.CLOSED]),
        )
    ) or 0

    return {
        'timezone': APP_TIME_ZONE,
        'pending_my_action': sum(len(actions) for actions in action_map.values()),
        'in_process': in_process,
        'closed_last_24h': closed_24h,
        'last_31_days': {
            'created': sum(month_by_status.values()),
            'approved': month_by_status.get('APPROVED', 0) + month_by_status.get('CLOSED', 0),
            'closed': month_by_status.get('CLOSED', 0),
            'rejected': month_by_status.get('REJECTED', 0),
            'cancelled': month_by_status.get('CANCELLED', 0),
            'approved_amount': str(month_amount),
        },
        'pending_items': [
            {
                'request_id': item.request_id,
                'display_id': item.display_id,
                'title': item.title,
                'urgency': item.urgency,
                'status': item.status.value,
                'created_at': _as_utc(item.created_at),
                'actions': action_map.get(item.id, []),
            }
            for item in pending_items
        ],
    }
