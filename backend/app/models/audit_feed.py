"""Canonical append-only change feed used by the audit API.

Business mutations calculate their field-level delta once, in the same
transaction, and persist it here.  Reads never rebuild history from domain
tables.
"""

from __future__ import annotations

import enum
import json
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    select,
)
from sqlalchemy.engine import Connection
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.database import Base


AUDIT_JSON = JSON().with_variant(JSONB(), 'postgresql')


class AuditChangeFeed(Base):
    """One immutable row per auditable change or domain event."""

    __tablename__ = 'audit_change_feed'
    __table_args__ = (
        CheckConstraint(
            "change_type IN ('CREATE', 'UPDATE', 'DELETE')",
            name='ck_audit_change_feed_change_type',
        ),
        UniqueConstraint(
            'source_type',
            'source_id',
            name='uq_audit_change_feed_source',
        ),
        Index(
            'ix_audit_change_feed_occurred_sequence',
            'occurred_at',
            'event_sequence',
        ),
        Index(
            'ix_audit_change_feed_kind_occurred_sequence',
            'kind',
            'occurred_at',
            'event_sequence',
        ),
        Index(
            'ix_audit_change_feed_entity_sequence',
            'entity_type',
            'entity_id',
            'event_sequence',
        ),
    )

    event_sequence: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, 'sqlite'),
        primary_key=True,
        autoincrement=True,
    )
    event_id: Mapped[str] = mapped_column(
        String(160),
        unique=True,
        nullable=False,
        default=lambda: str(uuid.uuid4()),
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    change_type: Mapped[str] = mapped_column(String(10), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    actor_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actor_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    actor_label: Mapped[str] = mapped_column(String(255), nullable=False)
    changed_fields: Mapped[list] = mapped_column(AUDIT_JSON, nullable=False)
    changes: Mapped[dict] = mapped_column(AUDIT_JSON, nullable=False)
    snapshot: Mapped[dict | None] = mapped_column(AUDIT_JSON, nullable=True)
    event_context: Mapped[dict] = mapped_column(AUDIT_JSON, nullable=False, default=dict)
    search_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source_id: Mapped[str] = mapped_column(String(120), nullable=False)
    visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


SENSITIVE_FIELD_NAMES = {
    'access_token',
    'password',
    'password_hash',
    'reset_token',
    'secret',
    'secret_key',
    'temporary_password',
    'token',
}


def is_sensitive_field(field: str) -> bool:
    normalized = field.strip().lower()
    return (
        normalized in SENSITIVE_FIELD_NAMES
        or normalized.endswith('_token')
        or normalized.endswith('_hash')
        or normalized.endswith('_secret')
    )


def json_value(value):
    """Return a deterministic JSON-safe value without secrets."""

    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {
            str(key): json_value(item)
            for key, item in value.items()
            if not is_sensitive_field(str(key))
        }
    if isinstance(value, (list, tuple, set)):
        return [json_value(item) for item in value]
    return value


def field_changes(
    before_state: dict | None,
    after_state: dict | None,
) -> tuple[list[str], dict]:
    before = json_value(before_state) if before_state is not None else None
    after = json_value(after_state) if after_state is not None else None
    before_values = before or {}
    after_values = after or {}
    fields = sorted(
        field
        for field in set(before_values) | set(after_values)
        if not is_sensitive_field(field)
        and before_values.get(field) != after_values.get(field)
    )
    return fields, {
        field: {
            'before': before_values.get(field),
            'after': after_values.get(field),
        }
        for field in fields
    }


def latest_snapshot(
    connection: Connection,
    *,
    entity_type: str,
    entity_id: int | str,
) -> dict | None:
    table = AuditChangeFeed.__table__
    return connection.execute(
        select(table.c.snapshot)
        .where(
            table.c.entity_type == entity_type,
            table.c.entity_id == str(entity_id),
            table.c.snapshot.is_not(None),
        )
        .order_by(table.c.event_sequence.desc())
        .limit(1)
    ).scalar_one_or_none()


def _actor(connection: Connection, fallback_identifier: str | None = None) -> dict:
    actor = connection.info.get('audit_actor') or {}
    identifier = actor.get('identifier') or fallback_identifier or 'SYSTEM'
    label = actor.get('label')
    if not label:
        label = identifier if not identifier.upper().startswith('SYSTEM') and '@' not in identifier else 'Sistema'
    return {
        'user_id': actor.get('user_id'),
        'identifier': identifier,
        'label': label,
    }


def insert_change_event(
    connection: Connection,
    *,
    kind: str,
    entity_type: str,
    entity_id: int | str | None,
    event_type: str,
    change_type: str,
    subject: str,
    before_state: dict | None,
    after_state: dict | None,
    event_context: dict | None = None,
    occurred_at: datetime | None = None,
    source_type: str = 'DOMAIN',
    source_id: str | None = None,
    fallback_actor_identifier: str | None = None,
    visible: bool = True,
    event_id: str | None = None,
) -> str | None:
    """Insert one event using the caller's transaction.

    A no-op update is ignored.  CREATE and DELETE retain an explicit delta for
    every safe field, so the API never has to compare snapshots while reading.
    """

    safe_before = json_value(before_state) if before_state is not None else None
    safe_after = json_value(after_state) if after_state is not None else None
    changed_fields, changes = field_changes(safe_before, safe_after)
    if change_type == 'UPDATE' and not changed_fields:
        return None

    normalized_event_id = event_id or str(uuid.uuid4())
    normalized_source_id = source_id or normalized_event_id
    actor = _actor(connection, fallback_actor_identifier)
    context = json_value(event_context or {})
    snapshot = safe_after if safe_after is not None else safe_before
    searchable = ' '.join(filter(None, (
        str(subject),
        str(actor['label']),
        event_type,
        entity_type,
        json.dumps(changes, ensure_ascii=False, sort_keys=True),
        json.dumps(context, ensure_ascii=False, sort_keys=True),
    )))

    values = {
        'event_id': normalized_event_id,
        'kind': kind,
        'entity_type': entity_type,
        'entity_id': str(entity_id) if entity_id is not None else None,
        'event_type': event_type,
        'change_type': change_type,
        'subject': str(subject)[:255],
        'actor_user_id': actor['user_id'],
        'actor_identifier': str(actor['identifier'])[:255],
        'actor_label': str(actor['label'])[:255],
        'changed_fields': changed_fields,
        'changes': changes,
        'snapshot': snapshot,
        'event_context': context,
        'search_text': searchable,
        'source_type': source_type,
        'source_id': str(normalized_source_id)[:120],
        'visible': visible,
        'schema_version': 1,
    }
    if occurred_at is not None:
        values['occurred_at'] = occurred_at
    connection.execute(AuditChangeFeed.__table__.insert().values(**values))
    return normalized_event_id


def record_change_event(db: Session, **kwargs) -> str | None:
    """Session-friendly facade for explicit domain events."""

    return insert_change_event(db.connection(), **kwargs)


def override_entity_event(
    db: Session,
    *,
    entity_type: type,
    entity_id: int,
    event_type: str,
) -> None:
    overrides = db.info.setdefault('audit_event_overrides', {})
    overrides[(entity_type, entity_id)] = event_type
