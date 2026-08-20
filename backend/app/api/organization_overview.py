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


def _effective_role_names(db: Session, user_id: int) -> list[str]:
    """Return access roles inherited from groups plus roles assigned directly.

    Cargos are intentionally excluded from access resolution. Permissions belong
    to roles; users receive those roles either directly or through groups.
    """
    direct = set(db.scalars(
        select(Role.name)
        .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
        .where(
            UserRoleAssignment.user_id == user_id,
            Role.active.is_(True),
            Role.system_managed.is_(False),
        )
    ).all())
    inherited = set(db.scalars(
        select(Role.name)
        .join(GroupRole, GroupRole.role_id == Role.id)
        .join(UserGroup, UserGroup.id == GroupRole.group_id)
        .join(GroupMember, GroupMember.group_id == UserGroup.id)
        .where(
            GroupMember.user_id == user_id,
            UserGroup.active.is_(True),
            Role.active.is_(True),
            Role.system_managed.is_(False),
        )
    ).all())
    return sorted(direct | inherited, key=str.casefold)


@router.get('/groups')
def group_overview(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission('requests:read')),
):
    """Read-only organization snapshot shown on the authenticated home page."""
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

    member_cache: dict[int, dict] = {}
    for member in {
        user.id: user
        for users in members_by_group.values()
        for user in users
    }.values():
        pending = pending_actions_by_expense(db, member)
        member_cache[member.id] = {
            'id': member.id,
            'name': member.name,
            'email': member.email,
            'roles': _effective_role_names(db, member.id),
            'pending_actions': sum(len(actions) for actions in pending.values()),
        }

    return {
        'groups': [
            {
                'id': group.id,
                'name': group.name,
                'description': group.description,
                'members': [member_cache[user.id] for user in members_by_group[group.id]],
            }
            for group in groups
        ]
    }
