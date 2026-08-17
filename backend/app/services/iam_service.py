from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.iam import (
    GroupMember,
    GroupRole,
    Permission,
    Role,
    RolePermission,
    UserGroup,
    UserPermission,
    UserRoleAssignment,
)


CORE_PERMISSION_CODES = (
    'requests:read',
    'requests:create',
    'requests:approve',
    'requests:close',
    'config:manage',
)


def effective_permission_codes(db: Session, user_id: int) -> set[str]:
    direct_permissions = set(db.scalars(
        select(Permission.code)
        .join(UserPermission, UserPermission.permission_id == Permission.id)
        .where(
            UserPermission.user_id == user_id,
            Permission.active.is_(True),
        )
    ).all())

    direct_role_permissions = set(db.scalars(
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
        .where(
            UserRoleAssignment.user_id == user_id,
            Role.active.is_(True),
            Permission.active.is_(True),
        )
    ).all())

    group_role_permissions = set(db.scalars(
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .join(GroupRole, GroupRole.role_id == Role.id)
        .join(UserGroup, UserGroup.id == GroupRole.group_id)
        .join(GroupMember, GroupMember.group_id == UserGroup.id)
        .where(
            GroupMember.user_id == user_id,
            UserGroup.active.is_(True),
            Role.active.is_(True),
            Permission.active.is_(True),
        )
    ).all())

    return direct_permissions | direct_role_permissions | group_role_permissions


def has_permission(db: Session, user_id: int, permission_code: str) -> bool:
    return permission_code in effective_permission_codes(db, user_id)


def permission_sources(db: Session, user_id: int) -> dict[str, list[str]]:
    sources: dict[str, set[str]] = defaultdict(set)

    for code in db.scalars(
        select(Permission.code)
        .join(UserPermission, UserPermission.permission_id == Permission.id)
        .where(UserPermission.user_id == user_id, Permission.active.is_(True))
    ).all():
        sources[code].add('Asignación directa')

    direct_role_rows = db.execute(
        select(Permission.code, Role.name)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
        .where(
            UserRoleAssignment.user_id == user_id,
            Role.active.is_(True),
            Permission.active.is_(True),
        )
    ).all()
    for code, role_name in direct_role_rows:
        sources[code].add(f'Rol directo: {role_name}')

    group_rows = db.execute(
        select(Permission.code, UserGroup.name, Role.name)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .join(GroupRole, GroupRole.role_id == Role.id)
        .join(UserGroup, UserGroup.id == GroupRole.group_id)
        .join(GroupMember, GroupMember.group_id == UserGroup.id)
        .where(
            GroupMember.user_id == user_id,
            UserGroup.active.is_(True),
            Role.active.is_(True),
            Permission.active.is_(True),
        )
    ).all()
    for code, group_name, role_name in group_rows:
        sources[code].add(f'Grupo {group_name} → {role_name}')

    return {code: sorted(values) for code, values in sorted(sources.items())}
