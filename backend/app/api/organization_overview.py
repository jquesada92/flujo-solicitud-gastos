from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_permission
from app.models.entities import User
from app.models.iam import GroupMember, GroupRole, Role, UserGroup, UserRoleAssignment
from app.services.pending_action_service import pending_actions_by_expense

router = APIRouter()


def _group_role_names(db: Session, user_id: int, group_id: int) -> list[str]:
    """Return the role explicitly assigned to this user inside this group."""
    return list(db.scalars(
        select(Role.name)
        .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
        .join(GroupRole, GroupRole.role_id == Role.id)
        .where(
            UserRoleAssignment.user_id == user_id,
            GroupRole.group_id == group_id,
            Role.active.is_(True),
            Role.system_managed.is_(False),
        )
        .order_by(Role.name)
    ).all())


@router.get('/groups')
def group_overview(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission('requests:read')),
):
    """Read-only team snapshot for the Seguimiento de usuarios screen."""
    groups = list(db.scalars(
        select(UserGroup)
        .where(UserGroup.active.is_(True))
        .order_by(UserGroup.name)
    ).all())

    members_by_group: dict[int, list[User]] = defaultdict(list)
    if groups:
        rows = db.execute(
            select(GroupMember.group_id, User)
            .join(User, User.id == GroupMember.user_id)
            .where(
                GroupMember.group_id.in_([group.id for group in groups]),
                User.active.is_(True),
            )
            .order_by(GroupMember.group_id, User.name, User.id)
        ).all()
        for group_id, user in rows:
            members_by_group[group_id].append(user)

    pending_by_user: dict[int, int] = {}
    for member in {
        user.id: user
        for users in members_by_group.values()
        for user in users
    }.values():
        pending = pending_actions_by_expense(db, member)
        pending_by_user[member.id] = sum(len(actions) for actions in pending.values())

    return {
        'groups': [
            {
                'id': group.id,
                'name': group.name,
                'description': group.description,
                'members': [
                    {
                        'id': user.id,
                        'name': user.name,
                        'roles': _group_role_names(db, user.id, group.id),
                        'pending_actions': pending_by_user.get(user.id, 0),
                    }
                    for user in members_by_group[group.id]
                ],
            }
            for group in groups
        ]
    }
