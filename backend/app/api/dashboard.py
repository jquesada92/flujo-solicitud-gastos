import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_permission
from app.models.entities import Expense, ExpenseStatus, User
from app.services.pending_action_service import pending_actions_by_expense

router = APIRouter()
APP_TIME_ZONE = os.getenv('APP_TIME_ZONE', 'America/Panama')


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


@router.get('/dashboard')
def dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission('requests:read')),
):
    """Home dashboard backed by the canonical pending-action resolver."""
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
    in_process = db.scalar(select(func.count(Expense.id)).where(
        Expense.status.in_(open_statuses),
    )) or 0
    closed_24h = db.scalar(select(func.count(Expense.id)).where(
        Expense.status == ExpenseStatus.CLOSED,
        Expense.closed_at >= now_utc - timedelta(hours=24),
    )) or 0

    pending = pending_actions_by_expense(db, user)
    pending_ids = list(pending)
    pending_items = list(db.scalars(
        select(Expense)
        .where(Expense.id.in_(pending_ids))
        .order_by(Expense.created_at.asc())
        .limit(8)
    ).all()) if pending_ids else []

    month_rows = db.execute(
        select(Expense.status, func.count(Expense.id))
        .where(Expense.created_at >= period_start_utc)
        .group_by(Expense.status)
    ).all()
    month_by_status = {status.value: count for status, count in month_rows}
    month_amount = db.scalar(select(func.coalesce(func.sum(Expense.amount), 0)).where(
        Expense.created_at >= period_start_utc,
        Expense.status.in_([ExpenseStatus.APPROVED, ExpenseStatus.CLOSED]),
    )) or 0

    return {
        'timezone': APP_TIME_ZONE,
        'pending_my_action': sum(len(actions) for actions in pending.values()),
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
                'actions': pending.get(item.id, []),
            }
            for item in pending_items
        ],
    }
