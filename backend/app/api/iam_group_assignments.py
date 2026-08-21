from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_permission
from app.models.iam import GroupMember, GroupRole, Role, UserGroup, UserRoleAssignment

router = APIRouter(dependencies=[Depends(require_permission('config:manage'))])


class GroupAccessUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=1000)
    active: bool | None = None
    role_ids: list[int] | None = Field(default=None, max_length=100)
    # Compatibility input only. Membership is derived from user role assignments.
    member_ids: list[int] | None = Field(default=None, max_length=500)


def _out(db: Session, group: UserGroup) -> dict:
    return {
        'id': group.id,
        'code': group.code,
        'name': group.name,
        'description': group.description,
        'active': group.active,
        'role_ids': list(db.scalars(
            select(GroupRole.role_id)
            .where(GroupRole.group_id == group.id)
            .order_by(GroupRole.role_id)
        ).all()),
        'member_ids': list(db.scalars(
            select(GroupMember.user_id)
            .where(GroupMember.group_id == group.id)
            .order_by(GroupMember.user_id)
        ).all()),
    }


def _replace_group_roles(db: Session, group: UserGroup, role_ids: list[int]) -> None:
    unique_ids = list(dict.fromkeys(role_ids))
    roles = list(db.scalars(select(Role).where(
        Role.id.in_(unique_ids),
        Role.active.is_(True),
        Role.system_managed.is_(False),
    )).all()) if unique_ids else []
    if len(roles) != len(unique_ids):
        raise HTTPException(status_code=422, detail='Uno o más roles no existen, están inactivos o son técnicos')

    # One role belongs to one group. A role cannot be reused in several groups.
    conflicting = db.execute(
        select(GroupRole.role_id, UserGroup.name)
        .join(UserGroup, UserGroup.id == GroupRole.group_id)
        .where(
            GroupRole.role_id.in_(unique_ids),
            GroupRole.group_id != group.id,
        )
    ).first() if unique_ids else None
    if conflicting:
        role_id, other_group_name = conflicting
        role_name = next((role.name for role in roles if role.id == role_id), str(role_id))
        raise HTTPException(
            status_code=409,
            detail=f'El rol {role_name} ya pertenece al grupo {other_group_name}',
        )

    current_role_ids = set(db.scalars(
        select(GroupRole.role_id).where(GroupRole.group_id == group.id)
    ).all())
    removed_role_ids = current_role_ids - set(unique_ids)
    if removed_role_ids:
        assigned_role = db.scalar(
            select(UserRoleAssignment.role_id)
            .where(UserRoleAssignment.role_id.in_(removed_role_ids))
            .limit(1)
        )
        if assigned_role is not None:
            role_name = db.scalar(select(Role.name).where(Role.id == assigned_role)) or str(assigned_role)
            raise HTTPException(
                status_code=409,
                detail=f'No puedes quitar el rol {role_name} del grupo mientras tenga usuarios asignados',
            )

    db.execute(delete(GroupRole).where(GroupRole.group_id == group.id))
    db.add_all(GroupRole(group_id=group.id, role_id=role.id) for role in roles)


@router.patch('/groups/{group_id}')
def update_group_access(
    group_id: int,
    payload: GroupAccessUpdate,
    db: Session = Depends(get_db),
):
    """Persist group metadata and its role catalog in one transaction.

    Users are not added to a group directly. Selecting one role from that group
    on the user screen creates/removes the membership atomically.
    """
    group = db.get(UserGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail='Grupo no encontrado')

    changes = payload.model_dump(exclude_unset=True)
    if 'name' in changes:
        name = changes['name'].strip()
        duplicate = db.scalar(select(UserGroup.id).where(
            func.lower(UserGroup.name) == name.lower(),
            UserGroup.id != group.id,
        ))
        if duplicate:
            raise HTTPException(status_code=409, detail='Ya existe un grupo con ese nombre')
        group.name = name
    if 'description' in changes:
        group.description = changes['description'].strip() if changes['description'] else None
    if 'active' in changes:
        group.active = changes['active']

    if payload.role_ids is not None:
        _replace_group_roles(db, group, payload.role_ids)

    if payload.member_ids is not None:
        current_member_ids = set(db.scalars(
            select(GroupMember.user_id).where(GroupMember.group_id == group.id)
        ).all())
        if set(payload.member_ids) != current_member_ids:
            raise HTTPException(
                status_code=422,
                detail='Los miembros del grupo se administran asignando un rol del grupo al usuario',
            )

    db.commit()
    db.refresh(group)
    return _out(db, group)
