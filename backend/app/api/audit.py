import os
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.privacy import mask_email, mask_tail
from app.core.security import require_permission
from app.models.audit_feed import AuditChangeFeed, is_sensitive_field

router = APIRouter(dependencies=[Depends(require_permission('can_configure'))])

DEFAULT_AUDIT_WINDOW_DAYS = 7
AUDIT_PAGE_SIZE = 10
APP_TIME_ZONE = os.getenv('APP_TIME_ZONE', 'America/Panama')


def _date_range_bounds(
    date_from: date | None,
    date_to: date | None,
    *,
    now: datetime | None = None,
) -> tuple[datetime, datetime, datetime]:
    """Translate inclusive application dates into an indexed UTC interval."""

    app_zone = ZoneInfo(APP_TIME_ZONE)
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    current = current.astimezone(timezone.utc)
    today = current.astimezone(app_zone).date()

    if (date_from is None) != (date_to is None):
        raise HTTPException(
            status_code=422,
            detail='Indica juntas las fechas Desde y Hasta',
        )
    effective_to = date_to or today
    effective_from = date_from or (today - timedelta(days=DEFAULT_AUDIT_WINDOW_DAYS - 1))
    if effective_from > effective_to:
        raise HTTPException(
            status_code=422,
            detail='La fecha Desde no puede ser posterior a la fecha Hasta',
        )
    if effective_to == date.max:
        raise HTTPException(status_code=422, detail='La fecha Hasta no es válida')

    range_start = datetime.combine(
        effective_from,
        time.min,
        tzinfo=app_zone,
    ).astimezone(timezone.utc)
    range_end = datetime.combine(
        effective_to + timedelta(days=1),
        time.min,
        tzinfo=app_zone,
    ).astimezone(timezone.utc)
    return range_start, range_end, current


def _parse_cursor(cursor: str | None) -> tuple[datetime, int] | None:
    if not cursor:
        return None
    try:
        timestamp, sequence = cursor.rsplit('|', 1)
        parsed = datetime.fromisoformat(timestamp)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        parsed_sequence = int(sequence)
        if parsed_sequence < 1:
            raise ValueError('invalid sequence')
        return parsed, parsed_sequence
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail='Cursor de auditoría inválido') from exc


def _safe_value(field: str, value):
    if value is None:
        return None
    normalized = field.strip().lower()
    if normalized.endswith('email') and isinstance(value, str):
        return mask_email(value)
    if normalized in {'identity_document', 'actor_identity_document'} and isinstance(value, str):
        return mask_tail(value)
    if normalized == 'phone' and isinstance(value, str):
        return mask_tail(value)
    if isinstance(value, list):
        return [_safe_value(field, item) for item in value]
    if isinstance(value, dict):
        return {
            key: _safe_value(key, item)
            for key, item in value.items()
            if not is_sensitive_field(key)
        }
    return value


def _safe_mapping(value: dict | None) -> dict | None:
    if value is None:
        return None
    return {
        field: _safe_value(field, item)
        for field, item in value.items()
        if not is_sensitive_field(field)
    }


def _safe_changes(changes: dict | None) -> dict:
    return {
        field: {
            'before': _safe_value(field, values.get('before')),
            'after': _safe_value(field, values.get('after')),
        }
        for field, values in (changes or {}).items()
        if not is_sensitive_field(field) and isinstance(values, dict)
    }


@router.get('/events')
def list_audit_events(
    kind: str = Query('ALL', pattern='^(ALL|FLOW|USER|PERMISSION|AREA|RULE)$'),
    limit: int = Query(AUDIT_PAGE_SIZE, ge=1, le=100),
    cursor: str | None = Query(default=None, max_length=200),
    q: str | None = Query(default=None, max_length=120),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Read one indexed, keyset-paginated change feed query."""

    cursor_value = _parse_cursor(cursor)
    range_start, range_end, now = _date_range_bounds(date_from, date_to)
    stmt = select(AuditChangeFeed).where(
        AuditChangeFeed.visible.is_(True),
        AuditChangeFeed.occurred_at >= range_start,
        AuditChangeFeed.occurred_at < range_end,
        AuditChangeFeed.occurred_at <= now,
    )
    if kind != 'ALL':
        stmt = stmt.where(AuditChangeFeed.kind == kind)
    term = q.strip() if q and q.strip() else None
    if term:
        stmt = stmt.where(AuditChangeFeed.search_text.ilike(f'%{term}%'))
    if cursor_value:
        cursor_time, cursor_sequence = cursor_value
        stmt = stmt.where(or_(
            AuditChangeFeed.occurred_at < cursor_time,
            and_(
                AuditChangeFeed.occurred_at == cursor_time,
                AuditChangeFeed.event_sequence < cursor_sequence,
            ),
        ))

    rows = list(db.scalars(
        stmt.order_by(
            AuditChangeFeed.occurred_at.desc(),
            AuditChangeFeed.event_sequence.desc(),
        ).limit(limit + 1)
    ).all())
    has_more = len(rows) > limit
    page = rows[:limit]
    items = []
    for row in page:
        changes = _safe_changes(row.changes)
        items.append({
            'event_id': row.event_id,
            'occurred_at': row.occurred_at,
            'kind': row.kind,
            'entity_type': row.entity_type,
            'event_type': row.event_type,
            'change_type': row.change_type,
            'subject': row.subject,
            'actor': row.actor_label,
            'changed_fields': list(changes),
            'changes': changes,
            'details': _safe_mapping(row.snapshot),
            'context': _safe_mapping(row.event_context),
        })

    next_cursor = None
    if has_more and page:
        last = page[-1]
        next_cursor = f'{last.occurred_at.isoformat()}|{last.event_sequence}'
    return {'items': items, 'next_cursor': next_cursor, 'has_more': has_more}
