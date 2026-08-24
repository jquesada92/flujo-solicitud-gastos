import re
import unicodedata

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import current_user, require_permission
from app.models.entities import User
from app.models.iam import (
    GroupMember,
    GroupPermission,
    GroupRole,
    Permission,
    Position,
    Role,
    RolePermission,
    UserGroup,
    UserPermission,
    UserPosition,
    UserRoleAssignment,
)
from app.schemas.iam import (
    EffectiveAccessOut,
    GroupOut,
    GroupWrite,
    PermissionOut,
    PositionOut,
    PositionUpdate,
    PositionWrite,
    RoleOut,
    RoleUpdate,
    RoleWrite,
)
from app.services.iam_service import effective_permission_codes, permission_sources

router = APIRouter()


def _code(name: str) -> str:
    normalized = unicodedata.normalize('NFKD', name)
    ascii_name = ''.join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r'[^a-z0-9]+', '-', ascii_name.lower()).strip('-')[:90]


def _unique_code(db: Session, model, name: str) -> str:
    base = _code(name) or 'item'
    candidate = base
    sequence = 2
    while db.scalar(select(model.id).where(model.code == candidate)):
        candidate = f'{base}-{sequence}'
        sequence += 1
    return candidate


def _user(db: Session, user_id: int) -> User:
    item = db.get(User, user_id)
    if not item:
        raise HTTPException(status_code=404, detail='Usuario no encontrado')
    return item


def _role(db: Session, role_id: int) -> Role:
    item = db.get(Role, role_id)
    if not item:
        raise HTTPException(status_code=404, detail='Rol no encontrado')
    return item


def _group(db: Session, group_id: int) -> UserGroup:
    item = db.get(UserGroup, group_id)
    if not item:
        raise HTTPException(status_code=404, detail='Grupo no encontrado')
    return item


def _position(db: Session, position_id: int) -> Position:
    item = db.get(Position, position_id)
    if not item:
        raise HTTPException(status_code=404, detail='Cargo no encontrado')
    return item


def _permission(db: Session, code: str) -> Permission:
    item = db.scalar(select(Permission).where(Permission.code == code, Permission.active.is_(True)))
    if not item:
        raise HTTPException(status_code=422, detail=f'Permiso desconocido o inactivo: {code}')
    return item


def _role_out(db: Session, role: Role) -> RoleOut:
    codes = list(db.scalars(
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role.id)
        .order_by(Permission.code)
    ).all())
    return RoleOut(
        id=role.id,
        code=role.code,
        name=role.name,
        description=role.description,
        active=role.active,
        system_managed=role.system_managed,
        permission_codes=codes,
    )


def _group_out(db: Session, group: UserGroup) -> GroupOut:
    return GroupOut(
        id=group.id,
        code=group.code,
        name=group.name,
        description=group.description,
        active=group.active,
        permission_codes=list(db.scalars(
            select(Permission.code)
            .join(GroupPermission, GroupPermission.permission_id == Permission.id)
            .where(GroupPermission.group_id == group.id)
            .order_by(Permission.code)
        ).all()),
        role_ids=list(db.scalars(
            select(GroupRole.role_id).where(GroupRole.group_id == group.id).order_by(GroupRole.role_id)
        ).all()),
        member_ids=list(db.scalars(
            select(GroupMember.user_id).where(GroupMember.group_id == group.id).order_by(GroupMember.user_id)
        ).all()),
    )


def _replace_role_permissions(db: Session, role: Role, permission_codes: list[str]) -> None:
    unique_codes = list(dict.fromkeys(permission_codes))
    permissions = [_permission(db, code) for code in unique_codes]
    desired_ids = {permission.id for permission in permissions}
    current = list(db.scalars(
        select(RolePermission).where(RolePermission.role_id == role.id)
    ).all())
    current_ids = {assignment.permission_id for assignment in current}
    for assignment in current:
        if assignment.permission_id not in desired_ids:
            db.delete(assignment)
    db.add_all(
        RolePermission(role_id=role.id, permission_id=permission.id)
        for permission in permissions
        if permission.id not in current_ids
    )


def _replace_group_permissions(db: Session, group: UserGroup, permission_codes: list[str]) -> None:
    unique_codes = list(dict.fromkeys(permission_codes))
    permissions = [_permission(db, code) for code in unique_codes]
    desired_ids = {permission.id for permission in permissions}
    current = list(db.scalars(
        select(GroupPermission).where(GroupPermission.group_id == group.id)
    ).all())
    current_ids = {assignment.permission_id for assignment in current}
    for assignment in current:
        if assignment.permission_id not in desired_ids:
            db.delete(assignment)
    db.add_all(
        GroupPermission(group_id=group.id, permission_id=permission.id)
        for permission in permissions
        if permission.id not in current_ids
    )


@router.get('/me/permissions', response_model=EffectiveAccessOut)
def my_effective_permissions(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    return EffectiveAccessOut(
        user_id=user.id,
        permission_codes=sorted(effective_permission_codes(db, user.id)),
        sources=permission_sources(db, user.id),
    )


@router.get('/permissions', response_model=list[PermissionOut], dependencies=[Depends(require_permission('config:manage'))])
def list_permissions(db: Session = Depends(get_db)):
    return list(db.scalars(select(Permission).order_by(Permission.code)).all())


@router.get('/roles', response_model=list[RoleOut], dependencies=[Depends(require_permission('config:manage'))])
def list_roles(include_inactive: bool = False, db: Session = Depends(get_db)):
    stmt = select(Role).order_by(Role.name)
    if not include_inactive:
        stmt = stmt.where(Role.active.is_(True))
    return [_role_out(db, role) for role in db.scalars(stmt).all()]


@router.get('/roles/recovery', response_model=RoleOut | None, dependencies=[Depends(require_permission('config:manage'))])
def recover_role(name: str | None = None, code: str | None = None, db: Session = Depends(get_db)):
    if not (name and name.strip()) and not (code and code.strip()):
        raise HTTPException(status_code=422, detail='Indica el nombre o código del rol')
    identity_filter = Role.code == code.strip().lower() if code and code.strip() else func.lower(func.trim(Role.name)) == name.strip().lower()
    role = db.scalar(select(Role).where(
        identity_filter,
        Role.active.is_(False),
        Role.system_managed.is_(False),
    ))
    return _role_out(db, role) if role else None


@router.post('/roles', response_model=RoleOut, status_code=201, dependencies=[Depends(require_permission('config:manage'))])
def create_role(payload: RoleWrite, db: Session = Depends(get_db)):
    if db.scalar(select(Role.id).where(func.lower(Role.name) == payload.name.lower())):
        raise HTTPException(status_code=409, detail='Ya existe un rol con ese nombre')
    role = Role(
        code=_unique_code(db, Role, payload.name),
        name=payload.name.strip(),
        description=payload.description.strip() if payload.description else None,
        active=payload.active,
        system_managed=False,
    )
    db.add(role)
    db.flush()
    _replace_role_permissions(db, role, payload.permission_codes)
    db.commit()
    db.refresh(role)
    return _role_out(db, role)


@router.patch('/roles/{role_id}', response_model=RoleOut, dependencies=[Depends(require_permission('config:manage'))])
def update_role(role_id: int, payload: RoleUpdate, db: Session = Depends(get_db)):
    role = _role(db, role_id)
    if role.system_managed:
        raise HTTPException(status_code=409, detail='Los roles técnicos administrados por el sistema no pueden modificarse desde la interfaz')
    changes = payload.model_dump(exclude_unset=True)
    if 'name' in changes:
        duplicate = db.scalar(select(Role.id).where(func.lower(Role.name) == changes['name'].lower(), Role.id != role.id))
        if duplicate:
            raise HTTPException(status_code=409, detail='Ya existe un rol con ese nombre')
        role.name = changes['name'].strip()
    if 'description' in changes:
        role.description = changes['description'].strip() if changes['description'] else None
    if 'active' in changes:
        role.active = changes['active']
    if 'permission_codes' in changes:
        _replace_role_permissions(db, role, changes['permission_codes'])
    db.commit()
    db.refresh(role)
    return _role_out(db, role)


@router.get('/groups', response_model=list[GroupOut], dependencies=[Depends(require_permission('config:manage'))])
def list_groups(include_inactive: bool = False, db: Session = Depends(get_db)):
    stmt = select(UserGroup).order_by(UserGroup.name)
    if not include_inactive:
        stmt = stmt.where(UserGroup.active.is_(True))
    return [_group_out(db, group) for group in db.scalars(stmt).all()]


@router.get('/groups/recovery', response_model=GroupOut | None, dependencies=[Depends(require_permission('config:manage'))])
def recover_group(name: str | None = None, code: str | None = None, db: Session = Depends(get_db)):
    if not (name and name.strip()) and not (code and code.strip()):
        raise HTTPException(status_code=422, detail='Indica el nombre o código del grupo')
    identity_filter = UserGroup.code == code.strip().lower() if code and code.strip() else func.lower(func.trim(UserGroup.name)) == name.strip().lower()
    group = db.scalar(select(UserGroup).where(
        identity_filter,
        UserGroup.active.is_(False),
    ))
    return _group_out(db, group) if group else None


@router.post('/groups', response_model=GroupOut, status_code=201, dependencies=[Depends(require_permission('config:manage'))])
def create_group(payload: GroupWrite, db: Session = Depends(get_db)):
    if db.scalar(select(UserGroup.id).where(func.lower(UserGroup.name) == payload.name.lower())):
        raise HTTPException(status_code=409, detail='Ya existe un grupo con ese nombre')
    group = UserGroup(
        code=_unique_code(db, UserGroup, payload.name),
        name=payload.name.strip(),
        description=payload.description.strip() if payload.description else None,
        active=payload.active,
    )
    db.add(group)
    db.flush()
    _replace_group_permissions(db, group, payload.permission_codes)
    db.commit()
    db.refresh(group)
    return _group_out(db, group)


@router.put('/groups/{group_id}/roles/{role_id}', response_model=GroupOut, dependencies=[Depends(require_permission('config:manage'))])
def assign_role_to_group(group_id: int, role_id: int, db: Session = Depends(get_db)):
    group, role = _group(db, group_id), _role(db, role_id)
    if not db.scalar(select(GroupRole.id).where(GroupRole.group_id == group.id, GroupRole.role_id == role.id)):
        db.add(GroupRole(group_id=group.id, role_id=role.id))
        db.commit()
    return _group_out(db, group)


@router.delete('/groups/{group_id}/roles/{role_id}', response_model=GroupOut, dependencies=[Depends(require_permission('config:manage'))])
def remove_role_from_group(group_id: int, role_id: int, db: Session = Depends(get_db)):
    group = _group(db, group_id)
    db.execute(delete(GroupRole).where(GroupRole.group_id == group.id, GroupRole.role_id == role_id))
    db.commit()
    return _group_out(db, group)


@router.put('/groups/{group_id}/members/{user_id}', response_model=GroupOut, dependencies=[Depends(require_permission('config:manage'))])
def add_group_member(group_id: int, user_id: int, db: Session = Depends(get_db)):
    group, user = _group(db, group_id), _user(db, user_id)
    if not db.scalar(select(GroupMember.id).where(GroupMember.group_id == group.id, GroupMember.user_id == user.id)):
        db.add(GroupMember(group_id=group.id, user_id=user.id))
        db.commit()
    return _group_out(db, group)


@router.delete('/groups/{group_id}/members/{user_id}', response_model=GroupOut, dependencies=[Depends(require_permission('config:manage'))])
def remove_group_member(group_id: int, user_id: int, db: Session = Depends(get_db)):
    group = _group(db, group_id)
    db.execute(delete(GroupMember).where(GroupMember.group_id == group.id, GroupMember.user_id == user_id))
    db.commit()
    return _group_out(db, group)


@router.put('/users/{user_id}/roles/{role_id}', dependencies=[Depends(require_permission('config:manage'))])
def assign_direct_role(user_id: int, role_id: int, db: Session = Depends(get_db)):
    user, role = _user(db, user_id), _role(db, role_id)
    if not db.scalar(select(UserRoleAssignment.id).where(UserRoleAssignment.user_id == user.id, UserRoleAssignment.role_id == role.id)):
        db.add(UserRoleAssignment(user_id=user.id, role_id=role.id))
        db.commit()
    return {'status': 'ok'}


@router.delete('/users/{user_id}/roles/{role_id}', dependencies=[Depends(require_permission('config:manage'))])
def remove_direct_role(user_id: int, role_id: int, db: Session = Depends(get_db)):
    _user(db, user_id)
    db.execute(delete(UserRoleAssignment).where(UserRoleAssignment.user_id == user_id, UserRoleAssignment.role_id == role_id))
    db.commit()
    return {'status': 'ok'}


@router.put('/users/{user_id}/permissions/{permission_code}', dependencies=[Depends(require_permission('config:manage'))])
def grant_direct_permission(user_id: int, permission_code: str, db: Session = Depends(get_db)):
    user, permission = _user(db, user_id), _permission(db, permission_code)
    if not db.scalar(select(UserPermission.id).where(UserPermission.user_id == user.id, UserPermission.permission_id == permission.id)):
        db.add(UserPermission(user_id=user.id, permission_id=permission.id))
        db.commit()
    return {'status': 'ok'}


@router.delete('/users/{user_id}/permissions/{permission_code}', dependencies=[Depends(require_permission('config:manage'))])
def revoke_direct_permission(user_id: int, permission_code: str, db: Session = Depends(get_db)):
    user, permission = _user(db, user_id), _permission(db, permission_code)
    db.execute(delete(UserPermission).where(UserPermission.user_id == user.id, UserPermission.permission_id == permission.id))
    db.commit()
    return {'status': 'ok'}


@router.get('/users/{user_id}/effective-permissions', response_model=EffectiveAccessOut, dependencies=[Depends(require_permission('config:manage'))])
def user_effective_permissions(user_id: int, db: Session = Depends(get_db)):
    _user(db, user_id)
    return EffectiveAccessOut(
        user_id=user_id,
        permission_codes=sorted(effective_permission_codes(db, user_id)),
        sources=permission_sources(db, user_id),
    )


@router.get('/positions', response_model=list[PositionOut], dependencies=[Depends(require_permission('config:manage'))])
def list_positions(db: Session = Depends(get_db)):
    return list(db.scalars(select(Position).order_by(Position.name)).all())


@router.post('/positions', response_model=PositionOut, status_code=201, dependencies=[Depends(require_permission('config:manage'))])
def create_position(payload: PositionWrite, db: Session = Depends(get_db)):
    if db.scalar(select(Position.id).where(func.lower(Position.name) == payload.name.lower())):
        raise HTTPException(status_code=409, detail='Ya existe un cargo con ese nombre')
    position = Position(
        code=_unique_code(db, Position, payload.name),
        name=payload.name.strip(),
        description=payload.description.strip() if payload.description else None,
        active=payload.active,
    )
    db.add(position)
    db.commit()
    db.refresh(position)
    return position


@router.patch('/positions/{position_id}', response_model=PositionOut, dependencies=[Depends(require_permission('config:manage'))])
def update_position(position_id: int, payload: PositionUpdate, db: Session = Depends(get_db)):
    position = _position(db, position_id)
    changes = payload.model_dump(exclude_unset=True)
    if 'name' in changes:
        duplicate = db.scalar(select(Position.id).where(func.lower(Position.name) == changes['name'].lower(), Position.id != position.id))
        if duplicate:
            raise HTTPException(status_code=409, detail='Ya existe un cargo con ese nombre')
        position.name = changes['name'].strip()
    if 'description' in changes:
        position.description = changes['description'].strip() if changes['description'] else None
    if 'active' in changes:
        position.active = changes['active']
    db.commit()
    db.refresh(position)
    return position


@router.put('/users/{user_id}/positions/{position_id}', dependencies=[Depends(require_permission('config:manage'))])
def assign_position(user_id: int, position_id: int, db: Session = Depends(get_db)):
    user, position = _user(db, user_id), _position(db, position_id)
    if not db.scalar(select(UserPosition.id).where(UserPosition.user_id == user.id, UserPosition.position_id == position.id)):
        db.add(UserPosition(user_id=user.id, position_id=position.id))
        db.commit()
    return {'status': 'ok'}


@router.delete('/users/{user_id}/positions/{position_id}', dependencies=[Depends(require_permission('config:manage'))])
def remove_position(user_id: int, position_id: int, db: Session = Depends(get_db)):
    _user(db, user_id)
    db.execute(delete(UserPosition).where(UserPosition.user_id == user_id, UserPosition.position_id == position_id))
    db.commit()
    return {'status': 'ok'}
