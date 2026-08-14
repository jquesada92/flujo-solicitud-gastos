from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Text as SqlText, and_, cast, func, or_, select, text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_permission
from app.models.entities import (
    AccessProfileChangeEvent,
    ApprovalPolicyChangeEvent,
    ApprovalStepEvent,
    User,
    UserChangeEvent,
)

router = APIRouter(dependencies=[Depends(require_permission('can_configure'))])


def _period_filter(column):
    return column >= func.now() - text("INTERVAL '45 days'"), column <= func.now()


def _page_rows(db, model, limit, cursor_value, search_filter=None):
    stmt = select(model).where(*_period_filter(model.occurred_at))
    if search_filter is not None:
        stmt = stmt.where(search_filter)
    if cursor_value:
        cursor_time, cursor_id = cursor_value
        stmt = stmt.where(or_(
            model.occurred_at < cursor_time,
            and_(model.occurred_at == cursor_time, model.event_id < cursor_id),
        ))
    return db.scalars(stmt.order_by(model.occurred_at.desc(), model.event_id.desc()).limit(limit + 1)).all()


@router.get('/events')
def list_audit_events(
    kind: str = Query('ALL', pattern='^(ALL|FLOW|USER|PERMISSION|RULE)$'),
    limit: int = Query(50, ge=1, le=100),
    cursor: str | None = Query(default=None, max_length=100),
    q: str | None = Query(default=None, max_length=120),
    db: Session = Depends(get_db),
):
    cursor_value = None
    if cursor:
        timestamp, event_id = cursor.rsplit('|', 1)
        cursor_value = (datetime.fromisoformat(timestamp), event_id)
    users = db.scalars(select(User)).all()
    user_names_by_id = {user.id: user.full_name for user in users}
    user_names_by_email = {user.email.lower(): user.full_name for user in users}

    def actor_name(user_id=None, email=None):
        if user_id and user_id in user_names_by_id:
            return user_names_by_id[user_id]
        if email and email.lower() in user_names_by_email:
            return user_names_by_email[email.lower()]
        return 'Sistema'

    term = f"%{q.strip()}%" if q and q.strip() else None
    events = []
    if kind in ('ALL', 'FLOW'):
        search_filter = or_(
            ApprovalStepEvent.display_id.ilike(term), ApprovalStepEvent.request_id.ilike(term),
            ApprovalStepEvent.approver_email.ilike(term), ApprovalStepEvent.approver_role.ilike(term),
            ApprovalStepEvent.actor_email.ilike(term), cast(ApprovalStepEvent.payload, SqlText).ilike(term),
        ) if term else None
        rows = _page_rows(db, ApprovalStepEvent, limit, cursor_value, search_filter)
        events.extend({
            'event_id': row.event_id, 'occurred_at': row.occurred_at, 'kind': 'FLOW',
            'event_type': row.event_type, 'subject': row.display_id,
            'actor': actor_name(email=row.actor_email),
            'changed_fields': ['status'],
            'details': {'paso': row.step, 'cargo': row.approver_role,
                        'estado_anterior': row.previous_status, 'estado_nuevo': row.new_status,
                        'estado_solicitud': row.expense_status},
        } for row in rows)
    if kind in ('ALL', 'USER'):
        search_filter = or_(UserChangeEvent.user_email.ilike(term), UserChangeEvent.actor_email.ilike(term),
                            cast(UserChangeEvent.before_state, SqlText).ilike(term),
                            cast(UserChangeEvent.after_state, SqlText).ilike(term)) if term else None
        rows = _page_rows(db, UserChangeEvent, limit, cursor_value, search_filter)
        events.extend({
            'event_id': row.event_id, 'occurred_at': row.occurred_at, 'kind': 'USER',
            'event_type': row.event_type, 'subject': user_names_by_id.get(row.user_id, 'Usuario'),
            'actor': actor_name(user_id=row.actor_user_id),
            'changed_fields': row.changed_fields, 'details': row.after_state,
        } for row in rows)
    if kind in ('ALL', 'PERMISSION'):
        search_filter = or_(AccessProfileChangeEvent.profile_code.ilike(term), AccessProfileChangeEvent.actor_email.ilike(term),
                            cast(AccessProfileChangeEvent.before_state, SqlText).ilike(term),
                            cast(AccessProfileChangeEvent.after_state, SqlText).ilike(term)) if term else None
        rows = _page_rows(db, AccessProfileChangeEvent, limit, cursor_value, search_filter)
        events.extend({
            'event_id': row.event_id, 'occurred_at': row.occurred_at, 'kind': 'PERMISSION',
            'event_type': row.event_type, 'subject': row.profile_code,
            'actor': actor_name(user_id=row.actor_user_id),
            'changed_fields': row.changed_fields, 'details': row.after_state,
        } for row in rows)
    if kind in ('ALL', 'RULE'):
        search_filter = or_(ApprovalPolicyChangeEvent.policy_name.ilike(term), ApprovalPolicyChangeEvent.actor_email.ilike(term),
                            cast(ApprovalPolicyChangeEvent.before_state, SqlText).ilike(term),
                            cast(ApprovalPolicyChangeEvent.after_state, SqlText).ilike(term)) if term else None
        rows = _page_rows(db, ApprovalPolicyChangeEvent, limit, cursor_value, search_filter)
        events.extend({
            'event_id': row.event_id, 'occurred_at': row.occurred_at, 'kind': 'RULE',
            'event_type': row.event_type, 'subject': row.policy_name,
            'actor': actor_name(user_id=row.actor_user_id),
            'changed_fields': row.changed_fields, 'details': row.after_state or row.before_state,
        } for row in rows)
    events.sort(key=lambda item: (item['occurred_at'], item['event_id']), reverse=True)
    page = events[:limit]
    has_more = len(events) > limit
    next_cursor = None
    if has_more and page:
        last = page[-1]
        next_cursor = f"{last['occurred_at'].isoformat()}|{last['event_id']}"
    return {'items': page, 'next_cursor': next_cursor, 'has_more': has_more}
