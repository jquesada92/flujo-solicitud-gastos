from collections import defaultdict

from sqlalchemy import exists, select, union
from sqlalchemy.orm import Session

from app.models.entities import User
from app.models.iam import (
    GroupMember,
    GroupRole,
    Permission,
    Role,
    RolePermission,
    SystemAccount,
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
SYSTEM_ACCOUNT_ALLOWED_PERMISSIONS = {'requests:read', 'config:manage'}


def is_system_account(db: Session, user_id: int) -> bool:
    return db.scalar(select(SystemAccount.id).where(SystemAccount.user_id == user_id)) is not None


def _unrestricted_permission_codes(db: Session, user_id: int) -> set[str]:
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


def effective_permission_codes(db: Session, user_id: int) -> set[str]:
    permissions = _unrestricted_permission_codes(db, user_id)
    if is_system_account(db, user_id):
        return permissions & SYSTEM_ACCOUNT_ALLOWED_PERMISSIONS
    return permissions


def has_permission(db: Session, user_id: int, permission_code: str) -> bool:
    return permission_code in effective_permission_codes(db, user_id)


def users_with_permission(
    db: Session,
    permission_code: str,
    *,
    exclude_user_id: int | None = None,
    exclude_email: str | None = None,
) -> list[User]:
    """Resolve an active user population from IAM in one SQL query."""
    direct = (
        select(UserPermission.user_id.label('user_id'))
        .join(Permission, Permission.id == UserPermission.permission_id)
        .where(Permission.code == permission_code, Permission.active.is_(True))
    )
    direct_role = (
        select(UserRoleAssignment.user_id.label('user_id'))
        .join(Role, Role.id == UserRoleAssignment.role_id)
        .join(RolePermission, RolePermission.role_id == Role.id)
        .join(Permission, Permission.id == RolePermission.permission_id)
        .where(
            Permission.code == permission_code,
            Permission.active.is_(True),
            Role.active.is_(True),
        )
    )
    group_role = (
        select(GroupMember.user_id.label('user_id'))
        .join(UserGroup, UserGroup.id == GroupMember.group_id)
        .join(GroupRole, GroupRole.group_id == UserGroup.id)
        .join(Role, Role.id == GroupRole.role_id)
        .join(RolePermission, RolePermission.role_id == Role.id)
        .join(Permission, Permission.id == RolePermission.permission_id)
        .where(
            Permission.code == permission_code,
            Permission.active.is_(True),
            Role.active.is_(True),
            UserGroup.active.is_(True),
        )
    )
    permitted = union(direct, direct_role, group_role).subquery()
    stmt = select(User).join(permitted, permitted.c.user_id == User.id).where(User.active.is_(True))

    if permission_code not in SYSTEM_ACCOUNT_ALLOWED_PERMISSIONS:
        stmt = stmt.where(~exists(select(SystemAccount.id).where(SystemAccount.user_id == User.id)))
    if exclude_user_id is not None:
        stmt = stmt.where(User.id != exclude_user_id)
    if exclude_email:
        stmt = stmt.where(User.email.ilike(exclude_email).is_(False))
    return list(db.scalars(stmt.order_by(User.id)).all())


def permission_sources(db: Session, user_id: int) -> dict[str, list[str]]:
    effective = effective_permission_codes(db, user_id)
    sources: dict[str, set[str]] = defaultdict(set)

    for code in db.scalars(
        select(Permission.code)
        .join(UserPermission, UserPermission.permission_id == Permission.id)
        .where(UserPermission.user_id == user_id, Permission.active.is_(True))
    ).all():
        if code in effective:
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
        if code in effective:
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
        if code in effective:
            sources[code].add(f'Grupo {group_name} → {role_name}')

    if is_system_account(db, user_id):
        for code in effective:
            sources[code].add('Política de cuenta técnica')

    return {code: sorted(values) for code, values in sorted(sources.items())}
