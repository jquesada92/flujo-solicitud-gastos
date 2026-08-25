"""Temporal activity history for users and IAM catalog entities.

The mapper hooks keep the history in the same database transaction as the
entity mutation, including bootstrap, demo seeders and compatibility APIs.
"""

from datetime import datetime, timezone

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, event, select, text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Mapped, Session, mapped_column, object_session

from app.core.database import Base
from app.models.entities import ExpenseArea, User
from app.models.iam import (
    GroupPermission,
    GroupRole,
    Permission,
    Role,
    RolePermission,
    UserGroup,
    UserRoleAssignment,
)


class UserActivityPeriod(Base):
    __tablename__ = 'user_activity_periods'
    __table_args__ = (
        CheckConstraint('active_until IS NULL OR active_until >= active_from', name='ck_user_activity_period_dates'),
        Index('uq_user_activity_period_open', 'user_id', unique=True, postgresql_where=text('active_until IS NULL'), sqlite_where=text('active_until IS NULL')),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    active_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    active_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    values: Mapped[dict] = mapped_column(JSON, nullable=False)
    event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    actor_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    actor_identity_document: Mapped[str | None] = mapped_column(String(50), nullable=True)
    change_type: Mapped[str] = mapped_column(String(40), nullable=False)
    changed_fields: Mapped[list] = mapped_column(JSON, nullable=False)
    changes: Mapped[dict] = mapped_column(JSON, nullable=False)


class AreaActivityPeriod(Base):
    __tablename__ = 'area_activity_periods'
    __table_args__ = (
        CheckConstraint('active_until IS NULL OR active_until >= active_from', name='ck_area_activity_period_dates'),
        Index('uq_area_activity_period_open', 'area_id', unique=True, postgresql_where=text('active_until IS NULL'), sqlite_where=text('active_until IS NULL')),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    area_id: Mapped[int] = mapped_column(ForeignKey('expense_categories.id', ondelete='CASCADE'), nullable=False, index=True)
    active_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    active_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    values: Mapped[dict] = mapped_column(JSON, nullable=False)
    event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    actor_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    actor_identity_document: Mapped[str | None] = mapped_column(String(50), nullable=True)
    change_type: Mapped[str] = mapped_column(String(40), nullable=False)
    changed_fields: Mapped[list] = mapped_column(JSON, nullable=False)
    changes: Mapped[dict] = mapped_column(JSON, nullable=False)


class RoleActivityPeriod(Base):
    __tablename__ = 'role_activity_periods'
    __table_args__ = (
        CheckConstraint('active_until IS NULL OR active_until >= active_from', name='ck_role_activity_period_dates'),
        Index('uq_role_activity_period_open', 'role_id', unique=True, postgresql_where=text('active_until IS NULL'), sqlite_where=text('active_until IS NULL')),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey('roles.id', ondelete='CASCADE'), nullable=False, index=True)
    active_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    active_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    values: Mapped[dict] = mapped_column(JSON, nullable=False)
    event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    actor_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    actor_identity_document: Mapped[str | None] = mapped_column(String(50), nullable=True)
    change_type: Mapped[str] = mapped_column(String(40), nullable=False)
    changed_fields: Mapped[list] = mapped_column(JSON, nullable=False)
    changes: Mapped[dict] = mapped_column(JSON, nullable=False)


class GroupActivityPeriod(Base):
    __tablename__ = 'group_activity_periods'
    __table_args__ = (
        CheckConstraint('active_until IS NULL OR active_until >= active_from', name='ck_group_activity_period_dates'),
        Index('uq_group_activity_period_open', 'group_id', unique=True, postgresql_where=text('active_until IS NULL'), sqlite_where=text('active_until IS NULL')),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey('user_groups.id', ondelete='CASCADE'), nullable=False, index=True)
    active_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    active_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    values: Mapped[dict] = mapped_column(JSON, nullable=False)
    event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    actor_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    actor_identity_document: Mapped[str | None] = mapped_column(String(50), nullable=True)
    change_type: Mapped[str] = mapped_column(String(40), nullable=False)
    changed_fields: Mapped[list] = mapped_column(JSON, nullable=False)
    changes: Mapped[dict] = mapped_column(JSON, nullable=False)


_CONFIG = {
    User: (UserActivityPeriod.__table__, 'user_id'),
    ExpenseArea: (AreaActivityPeriod.__table__, 'area_id'),
    Role: (RoleActivityPeriod.__table__, 'role_id'),
    UserGroup: (GroupActivityPeriod.__table__, 'group_id'),
}


def _now_for(target) -> datetime:
    return datetime.now(timezone.utc)


def _created_at(target) -> datetime:
    created_at = target.created_at or _now_for(target)
    return created_at.replace(tzinfo=timezone.utc) if created_at.tzinfo is None else created_at


def _actor(connection: Connection) -> dict:
    return connection.info.get('audit_actor') or {
        'user_id': None,
        'identifier': 'SYSTEM',
        'identity_document': None,
    }


def _change_set(before: dict | None, after: dict) -> tuple[list[str], dict]:
    fields = sorted(key for key in set(before or {}) | set(after) if (before or {}).get(key) != after.get(key))
    return fields, {
        key: {'before': (before or {}).get(key), 'after': after.get(key)}
        for key in fields
    }


def _audit_values(connection: Connection, *, event_at: datetime, change_type: str, before: dict | None, after: dict) -> dict:
    actor = _actor(connection)
    fields, changes = _change_set(before, after)
    return {
        'event_at': event_at,
        'actor_user_id': actor['user_id'],
        'actor_identifier': actor['identifier'],
        'actor_identity_document': actor.get('identity_document'),
        'change_type': change_type,
        'changed_fields': fields,
        'changes': changes,
    }


def _snapshot_by_id(connection: Connection, entity_type, entity_id: int) -> dict:
    row = connection.execute(
        select(entity_type.__table__).where(entity_type.__table__.c.id == entity_id)
    ).mappings().one()
    if entity_type is User:
        assigned_roles = connection.execute(
            select(Role.id, Role.code, Role.name)
            .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
            .where(UserRoleAssignment.user_id == entity_id)
            .order_by(Role.code)
        ).mappings().all()
        return {
            'identity_document': row['identity_document'],
            'phone': row['phone'],
            'first_name': row['first_name'],
            'middle_name': row['middle_name'],
            'last_name': row['last_name'],
            'second_last_name': row['second_last_name'],
            'name': row['name'],
            'email': row['email'],
            'role': row['role'].value if hasattr(row['role'], 'value') else str(row['role']),
            'assigned_roles': [dict(item) for item in assigned_roles],
            'active': row['active'],
        }
    if entity_type is Role:
        group = connection.execute(
            select(UserGroup.id, UserGroup.code, UserGroup.name)
            .join(GroupRole, GroupRole.group_id == UserGroup.id)
            .where(GroupRole.role_id == entity_id)
        ).mappings().first()
        permission_codes = list(connection.scalars(
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == entity_id)
            .order_by(Permission.code)
        ))
        return {
            'code': row['code'],
            'name': row['name'],
            'description': row['description'],
            'system_managed': row['system_managed'],
            'max_users': row['max_users'],
            'group': dict(group) if group else None,
            'permission_codes': permission_codes,
            'active': row['active'],
        }
    if entity_type is UserGroup:
        permission_codes = list(connection.scalars(
            select(Permission.code)
            .join(GroupPermission, GroupPermission.permission_id == Permission.id)
            .where(GroupPermission.group_id == entity_id)
            .order_by(Permission.code)
        ))
        return {
            'code': row['code'],
            'name': row['name'],
            'description': row['description'],
            'permission_codes': permission_codes,
            'active': row['active'],
        }
    return {
        'code': row['code'],
        'name': row['name'],
        'active': row['active'],
    }


def _snapshot(connection: Connection, target) -> dict:
    return _snapshot_by_id(connection, type(target), target.id)


def _insert_initial(mapper, connection: Connection, target) -> None:
    table, foreign_key = _CONFIG[type(target)]
    started_at = _created_at(target)
    snapshot = _snapshot(connection, target)
    connection.execute(table.insert().values(**{
        foreign_key: target.id,
        'active_from': started_at,
        'active_until': None,
        'values': snapshot,
        **_audit_values(connection, event_at=started_at, change_type='CREATE', before=None, after=snapshot),
    }))


def _record_revision(mapper, connection: Connection, target) -> None:
    session = object_session(target)
    if session is not None and type(target) in {Role, UserGroup}:
        _queue_iam_history_revision(session, type(target), target.id, 'UPDATE')
        return
    table, foreign_key = _CONFIG[type(target)]
    previous = connection.execute(
        select(table.c['values']).where(table.c[foreign_key] == target.id, table.c.active_until.is_(None))
    ).scalar_one_or_none()
    snapshot = _snapshot(connection, target)
    if previous == snapshot:
        return
    changed_at = _now_for(target)
    connection.execute(
        table.update()
        .where(table.c[foreign_key] == target.id, table.c.active_until.is_(None))
        .values(active_until=changed_at)
    )
    connection.execute(table.insert().values(**{
        foreign_key: target.id,
        'active_from': changed_at,
        'active_until': None,
        'values': snapshot,
        **_audit_values(connection, event_at=changed_at, change_type='UPDATE', before=previous, after=snapshot),
    }))


def _revise_related(
    connection: Connection,
    entity_type,
    entity_id: int,
    *,
    change_type: str = 'RELATION_UPDATE',
) -> None:
    exists = connection.scalar(select(entity_type.__table__.c.id).where(entity_type.__table__.c.id == entity_id))
    if exists is None:
        return
    table, foreign_key = _CONFIG[entity_type]
    previous = connection.execute(
        select(table.c['values']).where(table.c[foreign_key] == entity_id, table.c.active_until.is_(None))
    ).scalar_one_or_none()
    snapshot = _snapshot_by_id(connection, entity_type, entity_id)
    if previous == snapshot:
        return
    changed_at = datetime.now(timezone.utc)
    connection.execute(
        table.update()
        .where(table.c[foreign_key] == entity_id, table.c.active_until.is_(None))
        .values(active_until=changed_at)
    )
    connection.execute(table.insert().values(**{
        foreign_key: entity_id,
        'active_from': changed_at,
        'active_until': None,
        'values': snapshot,
        **_audit_values(connection, event_at=changed_at, change_type=change_type, before=previous, after=snapshot),
    }))


def _queue_iam_history_revision(
    session: Session,
    entity_type,
    entity_id: int,
    change_type: str = 'RELATION_UPDATE',
) -> None:
    targets = session.info.setdefault('iam_history_targets', {})
    key = (entity_type, entity_id)
    if change_type == 'UPDATE' or key not in targets:
        targets[key] = change_type


def _role_group_changed(mapper, connection: Connection, target) -> None:
    session = object_session(target)
    if session is not None:
        _queue_iam_history_revision(session, Role, target.role_id)
    else:
        _revise_related(connection, Role, target.role_id)


def _user_role_changed(mapper, connection: Connection, target) -> None:
    _revise_related(connection, User, target.user_id)


@event.listens_for(Session, 'before_flush')
def _collect_permission_relation_changes(session: Session, flush_context, instances) -> None:
    """Coalesce IAM permission relation edits into one history revision per owner."""
    for item in session.new.union(session.deleted):
        if isinstance(item, RolePermission) and item.role_id is not None:
            _queue_iam_history_revision(session, Role, item.role_id)
        elif isinstance(item, GroupPermission) and item.group_id is not None:
            _queue_iam_history_revision(session, UserGroup, item.group_id)


@event.listens_for(Session, 'after_flush_postexec')
def _record_permission_relation_changes(session: Session, flush_context) -> None:
    targets = session.info.pop('iam_history_targets', {})
    if not targets:
        return
    connection = session.connection()
    ordered = sorted(targets.items(), key=lambda item: (item[0][0].__name__, item[0][1]))
    for (entity_type, entity_id), change_type in ordered:
        _revise_related(connection, entity_type, entity_id, change_type=change_type)


@event.listens_for(Session, 'after_soft_rollback')
def _discard_pending_permission_relation_changes(session: Session, previous_transaction) -> None:
    session.info.pop('iam_history_targets', None)


for _entity in _CONFIG:
    event.listen(_entity, 'after_insert', _insert_initial)
    event.listen(_entity, 'after_update', _record_revision)

for _event in ('after_insert', 'after_update', 'after_delete'):
    event.listen(GroupRole, _event, _role_group_changed)
    event.listen(UserRoleAssignment, _event, _user_role_changed)
