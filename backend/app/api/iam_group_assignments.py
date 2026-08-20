from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_permission
from app.models.entities import User
from app.models.iam import GroupMember, GroupRole, Role, UserGroup

router = APIRouter(dependencies=[Depends(require_permission('config:manage'))])


class GroupAccessUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=1000)
    active: bool | None = None
    role_ids: list[int] | None = Field(default=None, max_length=100)
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


@router.patch('/groups/{group_id}')
def update_group_access(
    group_id: int,
    payload: GroupAccessUpdate,
    db: Session = Depends(get_db),
):
    """Persist one group's metadata, roles and members in one transaction."""
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
        role_ids = list(dict.fromkeys(payload.role_ids))
        roles = list(db.scalars(select(Role).where(
            Role.id.in_(role_ids),
            Role.active.is_(True),
            Role.system_managed.is_(False),
        )).all()) if role_ids else []
        if len(roles) != len(role_ids):
            raise HTTPException(status_code=422, detail='Uno o más roles no existen, están inactivos o son técnicos')
        db.execute(delete(GroupRole).where(GroupRole.group_id == group.id))
        db.add_all(GroupRole(group_id=group.id, role_id=role.id) for role in roles)

    if payload.member_ids is not None:
        member_ids = list(dict.fromkeys(payload.member_ids))
        members = list(db.scalars(select(User).where(User.id.in_(member_ids))).all()) if member_ids else []
        if len(members) != len(member_ids):
            raise HTTPException(status_code=422, detail='Uno o más usuarios no existen')
        db.execute(delete(GroupMember).where(GroupMember.group_id == group.id))
        db.add_all(GroupMember(group_id=group.id, user_id=user.id) for user in members)

    db.commit()
    db.refresh(group)
    return _out(db, group)
