from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import or_, select, text
from sqlalchemy.orm import Session

from app.models.entities import ApprovalPolicy, Expense, User
from app.models.iam import (
    GroupPermission,
    GroupRole,
    Permission,
    Role,
    RolePermission,
    UserGroup,
    UserRoleAssignment,
)
from app.services.iam_service import users_with_permission


APPROVE_PERMISSION = 'requests:approve'
NO_APPROVAL_MODE = 'NO_APPROVAL'
VOTING_APPROVAL_MODES = {'ANY', 'MAJORITY', 'ALL'}
APPROVAL_MODES = VOTING_APPROVAL_MODES | {NO_APPROVAL_MODE}
DIRECT_EXPENSE_REQUIRED_DETAIL = (
    'Este Área y monto corresponden a una regla sin aprobación; '
    'usa POST /api/direct-expenses en lugar de crear una Solicitud'
)


@dataclass(frozen=True)
class ApproverRoleTarget:
    id: int
    name: str
    group_id: int | None
    group_name: str | None


@dataclass(frozen=True)
class ApproverGroupTarget:
    id: int
    name: str
    role_count: int


def _integer_ids(values: list | None) -> set[int]:
    result: set[int] = set()
    for value in values or []:
        if isinstance(value, bool):
            continue
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            continue
        if parsed > 0:
            result.add(parsed)
    return result


def _own_approver_role_ids(db: Session) -> set[int]:
    return set(db.scalars(
        select(RolePermission.role_id)
        .join(Permission, Permission.id == RolePermission.permission_id)
        .where(
            Permission.code == APPROVE_PERMISSION,
            Permission.active.is_(True),
        )
    ).all())


def _approver_group_ids(db: Session) -> set[int]:
    return set(db.scalars(
        select(GroupPermission.group_id)
        .join(Permission, Permission.id == GroupPermission.permission_id)
        .join(UserGroup, UserGroup.id == GroupPermission.group_id)
        .where(
            Permission.code == APPROVE_PERMISSION,
            Permission.active.is_(True),
            UserGroup.active.is_(True),
        )
    ).all())


def eligible_approver_targets(
    db: Session,
) -> tuple[list[ApproverRoleTarget], list[ApproverGroupTarget]]:
    """Return IAM targets that can actually contribute requests:approve.

    A grouped Role is eligible when its own permission or its active Group's
    inherited permission supplies approval. A selectable Group must supply the
    inherited permission itself; selecting it then expands through every active
    Role related to that Group. GroupMember never participates.
    """
    own_role_ids = _own_approver_role_ids(db)
    inherited_group_ids = _approver_group_ids(db)
    rows = db.execute(
        select(
            Role.id,
            Role.name,
            GroupRole.group_id,
            UserGroup.name.label('group_name'),
            UserGroup.active.label('group_active'),
        )
        .outerjoin(GroupRole, GroupRole.role_id == Role.id)
        .outerjoin(UserGroup, UserGroup.id == GroupRole.group_id)
        .where(
            Role.active.is_(True),
            Role.system_managed.is_(False),
        )
        .order_by(Role.name, Role.id)
    ).all()

    roles: list[ApproverRoleTarget] = []
    active_role_counts: dict[int, int] = {}
    for role_id, role_name, group_id, group_name, group_active in rows:
        if group_id is not None and group_active:
            active_role_counts[group_id] = active_role_counts.get(group_id, 0) + 1
        role_is_effective = (
            group_id is None and role_id in own_role_ids
        ) or (
            group_id is not None
            and bool(group_active)
            and (role_id in own_role_ids or group_id in inherited_group_ids)
        )
        if role_is_effective:
            roles.append(ApproverRoleTarget(
                id=role_id,
                name=role_name,
                group_id=group_id,
                group_name=group_name,
            ))

    groups = [
        ApproverGroupTarget(
            id=group_id,
            name=name,
            role_count=active_role_counts.get(group_id, 0),
        )
        for group_id, name in db.execute(
            select(UserGroup.id, UserGroup.name)
            .where(
                UserGroup.active.is_(True),
                UserGroup.id.in_(inherited_group_ids),
            )
            .order_by(UserGroup.name, UserGroup.id)
        ).all()
    ] if inherited_group_ids else []
    return roles, groups


def eligible_approver_role_ids(db: Session) -> set[int]:
    roles, _ = eligible_approver_targets(db)
    return {item.id for item in roles}


def eligible_approver_group_ids(db: Session) -> set[int]:
    _, groups = eligible_approver_targets(db)
    return {item.id for item in groups}


def lock_policy_resolution_scopes(db: Session, expense_area: str) -> None:
    """Serialize policy resolution with configuration changes in PostgreSQL."""
    if db.get_bind().dialect.name != 'postgresql':
        return
    for scope in sorted({expense_area, 'ALL'}):
        db.execute(
            text('SELECT pg_advisory_xact_lock(hashtext(:scope))'),
            {'scope': f'approval-policy:{scope}'},
        )


def is_no_approval_policy(policy: ApprovalPolicy) -> bool:
    return (
        policy.approval_mode == NO_APPROVAL_MODE
        and not (policy.approver_role_ids or [])
        and not (policy.approver_group_ids or [])
    )


def _policy_has_valid_configuration(policy: ApprovalPolicy) -> bool:
    if policy.approval_mode == NO_APPROVAL_MODE:
        return is_no_approval_policy(policy)
    role_ids = _integer_ids(policy.approver_role_ids)
    group_ids = _integer_ids(policy.approver_group_ids)
    return bool(role_ids or group_ids)


def find_applicable_policy(
    db: Session,
    expense_area: str,
    amount: Decimal,
) -> ApprovalPolicy | None:
    """Resolve one unambiguous policy using (minimum, maximum] intervals.

    Area-specific policies override the legacy ALL fallback. Multiple matches
    inside either scope indicate pre-existing invalid data and fail closed.
    """
    lock_policy_resolution_scopes(db, expense_area)
    for scope in (expense_area, 'ALL'):
        if scope == 'ALL' and expense_area == 'ALL':
            continue
        stored_matches = list(db.scalars(
            select(ApprovalPolicy)
            .where(
                ApprovalPolicy.active.is_(True),
                ApprovalPolicy.expense_type == scope,
                ApprovalPolicy.min_amount < amount,
                or_(
                    ApprovalPolicy.max_amount.is_(None),
                    ApprovalPolicy.max_amount >= amount,
                ),
            )
            .order_by(ApprovalPolicy.min_amount.desc(), ApprovalPolicy.id)
        ).all())
        # A row created by the retired profile-code UI is configuration
        # metadata, not an approver rule. It must behave exactly like no policy.
        matches = [item for item in stored_matches if _policy_has_valid_configuration(item)]
        if len(matches) > 1:
            raise ValueError(
                f'Hay más de una regla activa aplicable al área {scope} y al monto {amount}'
            )
        if matches:
            return matches[0]
    return None


def participants_for_policy(
    db: Session,
    policy: ApprovalPolicy | None,
    *,
    exclude_email: str,
) -> list[User]:
    """Expand a policy's Roles/Groups and intersect them with effective IAM."""
    if policy is not None and policy.approval_mode == NO_APPROVAL_MODE:
        # A direct-expense band cannot accidentally become an approval round.
        return []
    permitted = users_with_permission(
        db,
        APPROVE_PERMISSION,
        exclude_email=exclude_email,
    )
    if policy is None:
        return permitted

    configured_role_ids = _integer_ids(policy.approver_role_ids)
    configured_group_ids = _integer_ids(policy.approver_group_ids)
    # Defensive compatibility for callers holding an old in-memory object. The
    # policy resolver itself ignores these rows, so they never enable quorum
    # closure or filter IAM participation.
    if not configured_role_ids and not configured_group_ids:
        return permitted

    role_ids = configured_role_ids & eligible_approver_role_ids(db)
    group_ids = configured_group_ids & eligible_approver_group_ids(db)
    target_user_ids: set[int] = set()
    if role_ids:
        target_user_ids.update(db.scalars(
            select(UserRoleAssignment.user_id).where(
                UserRoleAssignment.role_id.in_(role_ids),
            )
        ).all())
    if group_ids:
        target_user_ids.update(db.scalars(
            select(UserRoleAssignment.user_id)
            .join(Role, Role.id == UserRoleAssignment.role_id)
            .join(GroupRole, GroupRole.role_id == Role.id)
            .join(UserGroup, UserGroup.id == GroupRole.group_id)
            .where(
                GroupRole.group_id.in_(group_ids),
                Role.active.is_(True),
                Role.system_managed.is_(False),
                UserGroup.active.is_(True),
            )
        ).all())
    return [user for user in permitted if user.id in target_user_ids]


def minimum_votes_for_mode(mode: str, participant_count: int) -> int:
    if participant_count < 1:
        raise ValueError('La ronda requiere al menos un participante elegible')
    if mode == 'ANY':
        return 1
    if mode == 'MAJORITY':
        return participant_count // 2 + 1
    if mode == 'ALL':
        return participant_count
    raise ValueError(f'La regla tiene una modalidad de aprobación inválida: {mode}')


def snapshot_policy_resolution(
    expense: Expense,
    policy: ApprovalPolicy | None,
    amount: Decimal,
    participant_count: int,
    *,
    default_mode: str,
) -> int:
    mode = policy.approval_mode if policy else default_mode
    required = minimum_votes_for_mode(mode, participant_count)
    expense.approval_policy_id = policy.id if policy else None
    expense.approval_policy_mode = mode if policy else None
    expense.policy_evaluation_amount = amount
    expense.minimum_votes_required = required
    return required
