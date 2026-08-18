"""Temporary one-way compatibility bridge from legacy user flags to IAM.

The legacy Users/Profile screens still write ``can_*`` fields. Runtime
authorization MUST NOT read those fields. Until those screens are retired, this
bridge observes legacy writes and seeds missing canonical direct permissions.

The bridge is deliberately additive only: it never removes a canonical IAM
assignment because that assignment may have been configured intentionally from
the new Access Management UI. Revocation belongs to canonical IAM.
"""

from sqlalchemy import event, inspect, insert, select
from sqlalchemy.engine import Connection

from app.models.entities import User, UserRole
from app.models.iam import Permission, UserPermission


LEGACY_TRUE_PERMISSION_MAP = {
    'can_request': 'requests:create',
    'can_approve': 'requests:approve',
    'can_configure': 'config:manage',
}


def _seed_true_permissions(connection: Connection, user: User) -> None:
    # Compatibility input only. Technical administrators are governed by the
    # system-account environment policy and must not receive financial grants
    # from a legacy business-user screen.
    if user.role == UserRole.ADMIN:
        return

    for field_name, permission_code in LEGACY_TRUE_PERMISSION_MAP.items():
        if not bool(getattr(user, field_name, False)):
            continue
        permission_id = connection.execute(
            select(Permission.id).where(
                Permission.code == permission_code,
                Permission.active.is_(True),
            )
        ).scalar_one_or_none()
        if permission_id is None:
            continue
        assignment_id = connection.execute(
            select(UserPermission.id).where(
                UserPermission.user_id == user.id,
                UserPermission.permission_id == permission_id,
            )
        ).scalar_one_or_none()
        if assignment_id is None:
            connection.execute(insert(UserPermission).values(
                user_id=user.id,
                permission_id=permission_id,
            ))


def _after_insert(_mapper, connection: Connection, user: User) -> None:
    _seed_true_permissions(connection, user)


def _after_update(_mapper, connection: Connection, user: User) -> None:
    state = inspect(user)
    if not any(state.attrs[field_name].history.has_changes() for field_name in LEGACY_TRUE_PERMISSION_MAP):
        return
    _seed_true_permissions(connection, user)


def register_legacy_iam_bridge() -> None:
    """Register mapper hooks once for legacy compatibility writes."""
    if not event.contains(User, 'after_insert', _after_insert):
        event.listen(User, 'after_insert', _after_insert)
    if not event.contains(User, 'after_update', _after_update):
        event.listen(User, 'after_update', _after_update)
