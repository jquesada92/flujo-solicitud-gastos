"""Transactional capture of domain changes into the canonical audit feed."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import event, select
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from app.models.audit_feed import insert_change_event, latest_snapshot
from app.models.classification import AreaCategoryLink, ExpenseCategoryCatalog
from app.models.entities import (
    AccessProfile,
    ApprovalPolicy,
    ApprovalStepEvent,
    DirectExpense,
    Expense,
    ExpenseArea,
    QuotationVoteEvent,
    User,
)
from app.models.iam import (
    GroupMember,
    GroupPermission,
    GroupRole,
    Permission,
    Position,
    PositionRole,
    Role,
    RolePermission,
    UserGroup,
    UserPermission,
    UserPosition,
    UserRoleAssignment,
)


@dataclass(frozen=True)
class EntityConfig:
    kind: str
    entity_type: str


ENTITY_CONFIG = {
    User: EntityConfig('USER', 'USER'),
    AccessProfile: EntityConfig('PERMISSION', 'PROFILE'),
    Role: EntityConfig('PERMISSION', 'ROLE'),
    UserGroup: EntityConfig('PERMISSION', 'GROUP'),
    Permission: EntityConfig('PERMISSION', 'PERMISSION'),
    Position: EntityConfig('PERMISSION', 'POSITION'),
    ExpenseArea: EntityConfig('AREA', 'AREA'),
    ExpenseCategoryCatalog: EntityConfig('AREA', 'CATEGORY'),
    ApprovalPolicy: EntityConfig('RULE', 'RULE'),
    Expense: EntityConfig('FLOW', 'FLOW'),
    DirectExpense: EntityConfig('FLOW', 'DIRECT_EXPENSE'),
}


RELATION_TARGETS = {
    UserRoleAssignment: ((User, 'user_id'),),
    UserPermission: ((User, 'user_id'),),
    UserPosition: ((User, 'user_id'), (Position, 'position_id')),
    RolePermission: ((Role, 'role_id'),),
    GroupPermission: ((UserGroup, 'group_id'),),
    GroupRole: ((Role, 'role_id'), (UserGroup, 'group_id')),
    GroupMember: ((User, 'user_id'), (UserGroup, 'group_id')),
    PositionRole: ((Position, 'position_id'), (Role, 'role_id')),
    AreaCategoryLink: (
        (ExpenseArea, 'area_id'),
        (ExpenseCategoryCatalog, 'category_id'),
    ),
}


_MISSING = object()


def _rows(connection: Connection, stmt) -> list[dict]:
    return [dict(row) for row in connection.execute(stmt).mappings().all()]


def _snapshot_user(connection: Connection, entity_id: int, row) -> dict:
    assigned_roles = _rows(
        connection,
        select(Role.id, Role.code, Role.name)
        .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
        .where(UserRoleAssignment.user_id == entity_id)
        .order_by(Role.code),
    )
    direct_permissions = list(connection.scalars(
        select(Permission.code)
        .join(UserPermission, UserPermission.permission_id == Permission.id)
        .where(UserPermission.user_id == entity_id)
        .order_by(Permission.code)
    ))
    positions = _rows(
        connection,
        select(Position.id, Position.code, Position.name)
        .join(UserPosition, UserPosition.position_id == Position.id)
        .where(UserPosition.user_id == entity_id)
        .order_by(Position.code),
    )
    groups = _rows(
        connection,
        select(UserGroup.id, UserGroup.code, UserGroup.name)
        .join(GroupMember, GroupMember.group_id == UserGroup.id)
        .where(GroupMember.user_id == entity_id)
        .order_by(UserGroup.code),
    )
    return {
        'identity_document': row['identity_document'],
        'phone': row['phone'],
        'first_name': row['first_name'],
        'middle_name': row['middle_name'],
        'last_name': row['last_name'],
        'second_last_name': row['second_last_name'],
        'name': row['name'],
        'email': row['email'],
        'role': row['role'],
        'title': row['title'],
        'assigned_roles': assigned_roles,
        'direct_permission_codes': direct_permissions,
        'positions': positions,
        'groups': groups,
        'active': row['active'],
        'can_request': row['can_request'],
        'can_approve': row['can_approve'],
        'can_view': row['can_view'],
        'can_configure': row['can_configure'],
        'must_change_password': row['must_change_password'],
        'session_version': row['session_version'],
        'password_reset_version': row['password_reset_version'],
    }


def _snapshot_role(connection: Connection, entity_id: int, row) -> dict:
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
    positions = _rows(
        connection,
        select(Position.id, Position.code, Position.name)
        .join(PositionRole, PositionRole.position_id == Position.id)
        .where(PositionRole.role_id == entity_id)
        .order_by(Position.code),
    )
    return {
        'code': row['code'],
        'name': row['name'],
        'description': row['description'],
        'system_managed': row['system_managed'],
        'max_users': row['max_users'],
        'group': dict(group) if group else None,
        'permission_codes': permission_codes,
        'positions': positions,
        'active': row['active'],
    }


def _snapshot_group(connection: Connection, entity_id: int, row) -> dict:
    permission_codes = list(connection.scalars(
        select(Permission.code)
        .join(GroupPermission, GroupPermission.permission_id == Permission.id)
        .where(GroupPermission.group_id == entity_id)
        .order_by(Permission.code)
    ))
    roles = _rows(
        connection,
        select(Role.id, Role.code, Role.name)
        .join(GroupRole, GroupRole.role_id == Role.id)
        .where(GroupRole.group_id == entity_id)
        .order_by(Role.code),
    )
    members = _rows(
        connection,
        select(User.id, User.name)
        .join(GroupMember, GroupMember.user_id == User.id)
        .where(GroupMember.group_id == entity_id)
        .order_by(User.name),
    )
    return {
        'code': row['code'],
        'name': row['name'],
        'description': row['description'],
        'permission_codes': permission_codes,
        'roles': roles,
        'members': members,
        'active': row['active'],
    }


def _snapshot_area(connection: Connection, entity_id: int, row) -> dict:
    categories = _rows(
        connection,
        select(
            ExpenseCategoryCatalog.id,
            ExpenseCategoryCatalog.code,
            ExpenseCategoryCatalog.name,
            ExpenseCategoryCatalog.active,
        )
        .join(AreaCategoryLink, AreaCategoryLink.category_id == ExpenseCategoryCatalog.id)
        .where(AreaCategoryLink.area_id == entity_id)
        .order_by(ExpenseCategoryCatalog.code),
    )
    return {
        'code': row['code'],
        'name': row['name'],
        'categories': categories,
        'active': row['active'],
    }


def _snapshot_category(connection: Connection, entity_id: int, row) -> dict:
    areas = _rows(
        connection,
        select(ExpenseArea.id, ExpenseArea.code, ExpenseArea.name)
        .join(AreaCategoryLink, AreaCategoryLink.area_id == ExpenseArea.id)
        .where(AreaCategoryLink.category_id == entity_id)
        .order_by(ExpenseArea.code),
    )
    return {
        'code': row['code'],
        'name': row['name'],
        'areas': areas,
        'active': row['active'],
    }


def _snapshot_position(connection: Connection, entity_id: int, row) -> dict:
    roles = _rows(
        connection,
        select(Role.id, Role.code, Role.name)
        .join(PositionRole, PositionRole.role_id == Role.id)
        .where(PositionRole.position_id == entity_id)
        .order_by(Role.code),
    )
    users = _rows(
        connection,
        select(User.id, User.name)
        .join(UserPosition, UserPosition.user_id == User.id)
        .where(UserPosition.position_id == entity_id)
        .order_by(User.name),
    )
    return {
        'code': row['code'],
        'name': row['name'],
        'description': row['description'],
        'roles': roles,
        'users': users,
        'active': row['active'],
    }


def snapshot_by_id(connection: Connection, entity_type: type, entity_id: int) -> dict | None:
    row = connection.execute(
        select(entity_type.__table__).where(entity_type.__table__.c.id == entity_id)
    ).mappings().first()
    if row is None:
        return None
    if entity_type is User:
        return _snapshot_user(connection, entity_id, row)
    if entity_type is Role:
        return _snapshot_role(connection, entity_id, row)
    if entity_type is UserGroup:
        return _snapshot_group(connection, entity_id, row)
    if entity_type is ExpenseArea:
        return _snapshot_area(connection, entity_id, row)
    if entity_type is ExpenseCategoryCatalog:
        return _snapshot_category(connection, entity_id, row)
    if entity_type is Position:
        return _snapshot_position(connection, entity_id, row)
    if entity_type is Permission:
        return {
            'code': row['code'],
            'name': row['name'],
            'description': row['description'],
            'active': row['active'],
        }
    if entity_type is AccessProfile:
        return {
            field: row[field]
            for field in (
                'code', 'name', 'can_request', 'can_approve', 'can_view',
                'can_configure', 'has_user_limit', 'max_users', 'active',
            )
        }
    if entity_type is ApprovalPolicy:
        return {
            field: row[field]
            for field in (
                'name', 'expense_type', 'min_amount', 'max_amount',
                'approval_mode', 'approver_profile_codes', 'approver_role_ids',
                'approver_group_ids', 'active',
            )
        }
    if entity_type is Expense:
        return {
            field: row[field]
            for field in (
                'display_id', 'request_id', 'flow_id', 'request_type', 'title',
                'expense_area', 'expense_category', 'urgency', 'amount',
                'supplier', 'status', 'cancelled_at', 'cancellation_reason',
                'closed_at', 'closure_notes', 'selected_quotation_id',
                'approval_policy_id', 'approval_policy_mode',
                'policy_evaluation_amount', 'minimum_votes_required',
            )
        }
    if entity_type is DirectExpense:
        return {
            field: row[field]
            for field in (
                'display_id', 'record_id', 'expense_area', 'supplier',
                'item_description', 'amount', 'requester_user_id',
                'requester_email', 'invoice_original_name',
                'invoice_content_type', 'invoice_size', 'approval_policy_id',
            )
        }
    raise TypeError(f'Unsupported audited entity: {entity_type.__name__}')


def _subject(config: EntityConfig, snapshot: dict | None, entity_id: int) -> str:
    values = snapshot or {}
    if config.entity_type in {'FLOW', 'DIRECT_EXPENSE'}:
        return values.get('display_id') or values.get('title') or str(entity_id)
    return values.get('name') or values.get('code') or values.get('email') or str(entity_id)


def _event_type(
    config: EntityConfig,
    operation: str,
    before: dict | None,
    after: dict | None,
) -> str:
    if operation == 'CREATE':
        return f'{config.entity_type}_CREATED'
    if operation == 'DELETE':
        return f'{config.entity_type}_DELETED'
    before_values, after_values = before or {}, after or {}
    changed = {
        field
        for field in set(before_values) | set(after_values)
        if before_values.get(field) != after_values.get(field)
    }
    active_before, active_after = before_values.get('active'), after_values.get('active')
    if active_before is not active_after:
        if active_after is False:
            return f'{config.entity_type}_DEACTIVATED'
        if active_before is False and active_after is True:
            return f'{config.entity_type}_REACTIVATED'
    if config.entity_type == 'USER' and 'assigned_roles' in changed:
        return 'USER_ROLES_UPDATED'
    if config.entity_type == 'USER' and changed.intersection({
        'title', 'role', 'can_request', 'can_approve', 'can_view',
        'can_configure', 'direct_permission_codes',
    }):
        return 'USER_ACCESS_UPDATED'
    if config.entity_type in {'ROLE', 'GROUP'} and 'permission_codes' in changed:
        return f'{config.entity_type}_PERMISSIONS_UPDATED'
    if config.entity_type == 'ROLE' and 'group' in changed:
        return 'ROLE_GROUP_UPDATED'
    if config.entity_type == 'AREA' and 'categories' in changed:
        return 'AREA_CATEGORIES_UPDATED'
    if config.entity_type == 'CATEGORY' and 'areas' in changed:
        return 'CATEGORY_AREAS_UPDATED'
    if config.entity_type == 'FLOW' and 'status' in changed:
        return 'REQUEST_STATUS_UPDATED'
    return f'{config.entity_type}_UPDATED'


def record_entity_revision(
    db: Session,
    entity_type: type,
    entity_id: int,
    *,
    event_type: str | None = None,
) -> str | None:
    """Capture a Core-SQL relation mutation that bypassed ORM mapper events."""

    db.flush()
    connection = db.connection()
    config = ENTITY_CONFIG[entity_type]
    key = (entity_type, entity_id)
    prepared = db.info.get('audit_before_snapshots', {})
    has_prepared_before = key in prepared
    prepared_before = prepared.pop(key, _MISSING)
    if not prepared:
        db.info.pop('audit_before_snapshots', None)
    feed_before = latest_snapshot(
        connection,
        entity_type=config.entity_type,
        entity_id=entity_id,
    )
    after = snapshot_by_id(connection, entity_type, entity_id)
    # A mapper/relation hook may already have persisted the same final state
    # during the flush above. In that case the explicit Core bridge is a no-op,
    # not a second semantic event.
    if feed_before == after:
        return None
    before = prepared_before if has_prepared_before else feed_before
    return insert_change_event(
        connection,
        kind=config.kind,
        entity_type=config.entity_type,
        entity_id=entity_id,
        event_type=event_type or _event_type(config, 'UPDATE', before, after),
        change_type='UPDATE',
        subject=_subject(config, after or before, entity_id),
        before_state=before,
        after_state=after,
        event_context={'captured_by': 'core-sql-bridge'},
        source_type='entity_change',
    )


def prepare_entity_revision(
    db: Session,
    entity_type: type,
    entity_id: int,
) -> dict | None:
    """Remember database state before a Core UPDATE/DELETE is executed.

    Session mapper hooks cannot observe ORM-enabled Core DML. Callers stage the
    affected aggregate before issuing that statement, then call
    ``record_entity_revision`` after applying the mutation. Repeated prepares
    coalesce on the first state so a multi-statement replacement has one
    baseline and no duplicate feed row.
    """

    key = (entity_type, entity_id)
    prepared = db.info.setdefault('audit_before_snapshots', {})
    if key not in prepared:
        prepared[key] = snapshot_by_id(db.connection(), entity_type, entity_id)
    return prepared[key]


def _remember_before_snapshot(
    session: Session,
    entity_type: type,
    entity_id: int,
) -> None:
    key = (entity_type, entity_id)
    prepared = session.info.setdefault('audit_before_snapshots', {})
    if key in prepared:
        return
    connection = session.connection()
    config = ENTITY_CONFIG[entity_type]
    # The feed is the last committed aggregate image. It must win when a Core
    # DELETE already ran in the same transaction before an ORM relation is
    # inserted (the common role-replacement path). Falling back to the live
    # row keeps first post-cutover changes correct for entities with no feed
    # baseline yet.
    before = latest_snapshot(
        connection,
        entity_type=config.entity_type,
        entity_id=entity_id,
    )
    if before is None:
        before = snapshot_by_id(connection, entity_type, entity_id)
    prepared[key] = before


def _remember_entity(session: Session, entity_type: type, entity_id: int, operation: str) -> None:
    if operation != 'CREATE':
        _remember_before_snapshot(session, entity_type, entity_id)
    pending = session.info.setdefault('audit_pending_entities', {})
    key = (entity_type, entity_id)
    current = pending.get(key)
    priority = {'UPDATE': 1, 'CREATE': 2, 'DELETE': 3}
    if current is None or priority[operation] > priority[current]:
        pending[key] = operation


@event.listens_for(Session, 'before_flush')
def collect_audit_changes(session: Session, flush_context, instances) -> None:
    pending_objects = session.info.setdefault('audit_pending_objects', {})
    pending_sources = session.info.setdefault('audit_pending_sources', [])

    for item in session.new:
        item_type = type(item)
        if item_type in ENTITY_CONFIG:
            pending_objects[(item_type, id(item))] = (item, 'CREATE')
        elif isinstance(item, (ApprovalStepEvent, QuotationVoteEvent)):
            pending_sources.append(item)

    for item in session.dirty:
        item_type = type(item)
        if item_type in ENTITY_CONFIG and session.is_modified(item, include_collections=False):
            entity_id = getattr(item, 'id', None)
            if entity_id is not None:
                _remember_before_snapshot(session, item_type, entity_id)
            pending_objects.setdefault((item_type, id(item)), (item, 'UPDATE'))

    for item in session.deleted:
        item_type = type(item)
        if item_type in ENTITY_CONFIG:
            entity_id = getattr(item, 'id', None)
            if entity_id is not None:
                _remember_before_snapshot(session, item_type, entity_id)
            pending_objects[(item_type, id(item))] = (item, 'DELETE')

    for item in session.new.union(session.deleted):
        for entity_type, id_attribute in RELATION_TARGETS.get(type(item), ()):
            entity_id = getattr(item, id_attribute, None)
            if entity_id is not None:
                _remember_entity(session, entity_type, entity_id, 'UPDATE')


def _record_domain_source(connection: Connection, item) -> None:
    if isinstance(item, ApprovalStepEvent):
        insert_change_event(
            connection,
            kind='FLOW',
            entity_type='APPROVAL_STEP',
            entity_id=item.approval_id,
            event_type=item.event_type,
            change_type='UPDATE',
            subject=item.display_id,
            before_state={'status': item.previous_status},
            after_state={'status': item.new_status},
            event_context={
                'expense_id': item.expense_id,
                'request_id': item.request_id,
                'flow_id': item.flow_id,
                'step': item.step,
                'approver_role': item.approver_role,
                'expense_status': item.expense_status,
                'comment': item.comment,
            },
            occurred_at=item.occurred_at,
            source_type='approval_step_events',
            source_id=item.event_id,
            fallback_actor_identifier=item.actor_email,
        )
        return
    if isinstance(item, QuotationVoteEvent):
        display_id = connection.scalar(
            select(Expense.display_id).where(Expense.id == item.expense_id)
        ) or item.flow_id
        insert_change_event(
            connection,
            kind='FLOW',
            entity_type='QUOTATION_VOTE',
            entity_id=f'{item.expense_id}:{item.voter_user_id}',
            event_type=(
                'QUOTATION_VOTE_CAST'
                if item.previous_option_id is None
                else 'QUOTATION_VOTE_CHANGED'
            ),
            change_type='CREATE' if item.previous_option_id is None else 'UPDATE',
            subject=display_id,
            before_state={
                'quotation_option_id': item.previous_option_id,
            } if item.previous_option_id is not None else None,
            after_state={'quotation_option_id': item.selected_option_id},
            event_context={
                'expense_id': item.expense_id,
                'flow_id': item.flow_id,
                'voter_role': item.voter_role,
            },
            occurred_at=item.occurred_at,
            source_type='quotation_vote_events',
            source_id=str(item.id),
            fallback_actor_identifier=item.voter_email,
        )


@event.listens_for(Session, 'after_flush_postexec')
def persist_audit_changes(session: Session, flush_context) -> None:
    pending_objects = session.info.pop('audit_pending_objects', {})
    pending_entities = session.info.pop('audit_pending_entities', {})
    pending_sources = session.info.pop('audit_pending_sources', [])
    if not pending_objects and not pending_entities and not pending_sources:
        return

    connection = session.connection()
    covered_expense_ids = {
        item.expense_id
        for item in pending_sources
        if isinstance(item, (ApprovalStepEvent, QuotationVoteEvent))
    }

    resolved = dict(pending_entities)
    for item, operation in pending_objects.values():
        entity_id = getattr(item, 'id', None)
        if entity_id is None:
            continue
        key = (type(item), entity_id)
        current = resolved.get(key)
        if operation == 'DELETE' or current is None or operation == 'CREATE':
            resolved[key] = operation

    overrides = session.info.get('audit_event_overrides', {})
    before_snapshots = session.info.get('audit_before_snapshots', {})
    for (entity_type, entity_id), operation in sorted(
        resolved.items(),
        key=lambda item: (ENTITY_CONFIG[item[0][0]].entity_type, item[0][1]),
    ):
        config = ENTITY_CONFIG[entity_type]
        key = (entity_type, entity_id)
        has_captured_before = key in before_snapshots
        before = before_snapshots.pop(key, _MISSING)
        if not has_captured_before:
            before = latest_snapshot(
                connection,
                entity_type=config.entity_type,
                entity_id=entity_id,
            )
        after = None if operation == 'DELETE' else snapshot_by_id(connection, entity_type, entity_id)
        effective_operation = operation
        if operation == 'UPDATE' and before is None and not has_captured_before:
            effective_operation = 'CREATE'
        event_type = overrides.pop(
            (entity_type, entity_id),
            _event_type(config, effective_operation, before, after),
        )
        insert_change_event(
            connection,
            kind=config.kind,
            entity_type=config.entity_type,
            entity_id=entity_id,
            event_type=event_type,
            change_type=effective_operation,
            subject=_subject(config, after or before, entity_id),
            before_state=before,
            after_state=after,
            event_context={'captured_by': 'sqlalchemy-unit-of-work'},
            source_type='entity_change',
            visible=not (
                entity_type is Expense
                and effective_operation == 'UPDATE'
                and entity_id in covered_expense_ids
            ),
        )

    for item in pending_sources:
        _record_domain_source(connection, item)

    if not overrides:
        session.info.pop('audit_event_overrides', None)
    if not before_snapshots:
        session.info.pop('audit_before_snapshots', None)


@event.listens_for(Session, 'after_commit')
def discard_unused_prepared_snapshots(session: Session) -> None:
    session.info.pop('audit_before_snapshots', None)


@event.listens_for(Session, 'after_soft_rollback')
def discard_pending_audit_changes(session: Session, previous_transaction) -> None:
    for key in (
        'audit_pending_objects',
        'audit_pending_entities',
        'audit_pending_sources',
        'audit_event_overrides',
        'audit_before_snapshots',
    ):
        session.info.pop(key, None)
