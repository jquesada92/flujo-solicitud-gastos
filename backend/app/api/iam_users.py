import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.privacy import analytics_identifier
from app.core.security import hash_password, normalize_email, require_permission
from app.models.entities import User, UserRole
from app.models.iam import (
    GroupMember,
    GroupRole,
    Permission,
    Position,
    Role,
    SystemAccount,
    UserGroup,
    UserPosition,
    UserRoleAssignment,
)
from app.schemas.iam_user import IamUserCreate, IamUserOut, IamUserUpdate
from app.services.email_service import send_user_access_updated, send_user_invitation
from app.services.iam_service import (
    active_role_assignment_count,
    effective_permission_codes,
    is_system_account,
    permission_sources,
)

router = APIRouter(dependencies=[Depends(require_permission('config:manage'))])


def _full_name(user: User) -> str:
    return ' '.join(
        item.strip()
        for item in (user.first_name, user.middle_name, user.last_name, user.second_last_name)
        if item and item.strip()
    ) or user.name


def _access_email_summary(db: Session, user: User) -> tuple[list[str], list[tuple[str, str]]]:
    """Return canonical Cargo names and effective IAM permissions for user emails."""
    position_names = list(db.scalars(
        select(Position.name)
        .join(UserPosition, UserPosition.position_id == Position.id)
        .where(UserPosition.user_id == user.id, Position.active.is_(True))
        .order_by(Position.name)
    ).all())
    effective_codes = effective_permission_codes(db, user.id)
    if not effective_codes:
        return position_names, []
    permissions_by_code = {
        item.code: item.name
        for item in db.scalars(
            select(Permission)
            .where(Permission.code.in_(effective_codes), Permission.active.is_(True))
            .order_by(Permission.name, Permission.code)
        ).all()
    }
    permissions = [
        (permissions_by_code.get(code, code), code)
        for code in sorted(effective_codes, key=lambda value: (permissions_by_code.get(value, value), value))
    ]
    return position_names, permissions


def _out(db: Session, user: User) -> IamUserOut:
    group_ids = list(db.scalars(
        select(GroupMember.group_id).where(GroupMember.user_id == user.id).order_by(GroupMember.group_id)
    ).all())
    role_ids = list(db.scalars(
        select(UserRoleAssignment.role_id)
        .where(UserRoleAssignment.user_id == user.id)
        .order_by(UserRoleAssignment.role_id)
    ).all())
    position_ids = list(db.scalars(
        select(UserPosition.position_id)
        .where(UserPosition.user_id == user.id)
        .order_by(UserPosition.position_id)
    ).all())
    return IamUserOut(
        id=user.id,
        name=_full_name(user),
        identity_document=user.identity_document,
        first_name=user.first_name,
        middle_name=user.middle_name,
        last_name=user.last_name,
        second_last_name=user.second_last_name,
        email=user.email,
        phone=user.phone,
        active=user.active,
        must_change_password=user.must_change_password,
        created_at=user.created_at,
        updated_at=user.updated_at,
        is_system_account=is_system_account(db, user.id),
        group_ids=group_ids,
        role_ids=role_ids,
        position_ids=position_ids,
        direct_permission_codes=[],
        effective_permission_codes=sorted(effective_permission_codes(db, user.id)),
        permission_sources=permission_sources(db, user.id),
    )


def _validate_role_assignments(db: Session, role_ids: list[int]) -> tuple[list[Role], list[UserGroup]]:
    """Validate a mix of grouped and global role assignments.

    A business role may belong to zero or one group. Grouped roles require an
    active group and a user may hold at most one role from each group. Global
    roles have no GroupRole row and therefore do not create GroupMember rows.
    """
    unique_role_ids = list(dict.fromkeys(role_ids))
    if not unique_role_ids:
        return [], []

    roles = list(db.scalars(
        select(Role)
        .where(
            Role.id.in_(unique_role_ids),
            Role.active.is_(True),
            Role.system_managed.is_(False),
        )
        .order_by(Role.id)
        .with_for_update()
    ).all())
    if len(roles) != len(unique_role_ids):
        raise HTTPException(status_code=422, detail='Uno o más roles no existen, están inactivos o son técnicos')

    binding_rows = db.execute(
        select(GroupRole.role_id, UserGroup)
        .join(UserGroup, UserGroup.id == GroupRole.group_id)
        .where(GroupRole.role_id.in_(unique_role_ids))
    ).all()
    group_by_role = {role_id: group for role_id, group in binding_rows}

    inactive_group_roles = [
        role_id for role_id, group in group_by_role.items()
        if not group.active
    ]
    if inactive_group_roles:
        raise HTTPException(
            status_code=422,
            detail='No se puede asignar un rol cuyo grupo está inactivo',
        )

    groups = [group_by_role[role_id] for role_id in unique_role_ids if role_id in group_by_role]
    group_ids = [group.id for group in groups]
    if len(group_ids) != len(set(group_ids)):
        raise HTTPException(
            status_code=422,
            detail='Solo se permite un rol por grupo para cada usuario',
        )
    return roles, groups


def _validate_positions(db: Session, position_ids: list[int]) -> list[Position]:
    unique_ids = list(dict.fromkeys(position_ids))
    positions = list(db.scalars(select(Position).where(
        Position.id.in_(unique_ids),
        Position.active.is_(True),
    )).all()) if unique_ids else []
    if len(positions) != len(unique_ids):
        raise HTTPException(status_code=422, detail='Uno o más cargos no existen o están inactivos')
    return positions


def _validate_derived_groups(requested_group_ids: list[int] | None, groups: list[UserGroup]) -> None:
    """Groups are output/compatibility only; grouped roles own membership."""
    if requested_group_ids is None:
        return
    requested = set(requested_group_ids)
    derived = {group.id for group in groups}
    if requested != derived:
        raise HTTPException(
            status_code=422,
            detail='Los grupos no se asignan directamente: selecciona un rol dentro de cada grupo',
        )


def _replace_assignments(
    db: Session,
    user: User,
    *,
    group_ids: list[int] | None = None,
    role_ids: list[int] | None = None,
    permission_codes: list[str] | None = None,
    position_ids: list[int] | None = None,
) -> None:
    if permission_codes:
        raise HTTPException(
            status_code=422,
            detail='Los permisos deben asignarse mediante roles; no se permiten permisos individuales',
        )

    current_role_ids = list(db.scalars(
        select(UserRoleAssignment.role_id).where(UserRoleAssignment.user_id == user.id)
    ).all())
    target_role_ids = current_role_ids if role_ids is None else list(dict.fromkeys(role_ids))
    roles, groups = _validate_role_assignments(db, target_role_ids)
    _validate_derived_groups(group_ids, groups)

    if user.active:
        for role in roles:
            if (
                role.max_users is not None
                and active_role_assignment_count(
                    db,
                    role.id,
                    exclude_user_id=user.id,
                ) >= role.max_users
            ):
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f'El rol {role.name} alcanzó su límite de '
                        f'{role.max_users} usuario(s) activo(s)'
                    ),
                )

    if group_ids is not None and role_ids is None:
        current_group_ids = set(db.scalars(
            select(GroupMember.group_id).where(GroupMember.user_id == user.id)
        ).all())
        if set(group_ids) != current_group_ids:
            raise HTTPException(
                status_code=422,
                detail='La membresía de grupo se modifica asignando un rol del grupo',
            )

    if role_ids is not None:
        # Role assignment is atomic. Group membership is rebuilt only from the
        # subset of roles that belong to a group; global roles remain ungrouped.
        db.execute(delete(UserRoleAssignment).where(UserRoleAssignment.user_id == user.id))
        db.execute(delete(GroupMember).where(GroupMember.user_id == user.id))
        db.add_all(UserRoleAssignment(user_id=user.id, role_id=role.id) for role in roles)
        db.add_all(GroupMember(user_id=user.id, group_id=group.id) for group in groups)

    if position_ids is not None:
        positions = _validate_positions(db, position_ids)
        db.execute(delete(UserPosition).where(UserPosition.user_id == user.id))
        db.add_all(UserPosition(user_id=user.id, position_id=item.id) for item in positions)


def _sync_legacy_display_fields(db: Session, user: User) -> None:
    """Mirror IAM into old fields so the legacy React screen remains readable."""
    permissions = effective_permission_codes(db, user.id)
    user.can_view = 'requests:read' in permissions
    user.can_request = 'requests:create' in permissions
    user.can_approve = 'requests:approve' in permissions
    user.can_configure = 'config:manage' in permissions
    if user.role != UserRole.ADMIN:
        user.role = (
            UserRole.APPROVER if user.can_approve
            else UserRole.REQUESTER if user.can_request
            else UserRole.VIEWER
        )


@router.get('', response_model=list[IamUserOut])
def list_users(include_inactive: bool = False, db: Session = Depends(get_db)):
    stmt = select(User).order_by(User.name)
    if not include_inactive:
        stmt = stmt.where(User.active.is_(True))
    return [_out(db, user) for user in db.scalars(stmt).all()]


@router.get('/recovery', response_model=IamUserOut | None)
def recover_user(identity_document: str, db: Session = Depends(get_db)):
    document = identity_document.strip().upper()
    user = db.scalar(select(User).where(
        func.upper(func.trim(User.identity_document)) == document,
        User.active.is_(False),
    ))
    return _out(db, user) if user else None


@router.post('', response_model=IamUserOut, status_code=201)
def create_user(payload: IamUserCreate, db: Session = Depends(get_db)):
    email = normalize_email(str(payload.email))
    document = payload.identity_document.strip().upper()
    if db.scalar(select(User.id).where(func.lower(User.email) == email)):
        raise HTTPException(status_code=409, detail='Ya existe un usuario con ese correo')
    if db.scalar(select(User.id).where(func.upper(func.trim(User.identity_document)) == document)):
        raise HTTPException(status_code=409, detail='Ya existe un usuario con esa identificación')

    roles, groups = _validate_role_assignments(db, payload.role_ids)
    _validate_derived_groups(payload.group_ids, groups)
    _validate_positions(db, payload.position_ids)

    temporary_password = secrets.token_urlsafe(15)
    full_name = ' '.join(
        part.strip()
        for part in (payload.first_name, payload.middle_name, payload.last_name, payload.second_last_name)
        if part and part.strip()
    )
    user = User(
        name=full_name,
        first_name=payload.first_name.strip(),
        middle_name=payload.middle_name.strip() if payload.middle_name else None,
        last_name=payload.last_name.strip(),
        second_last_name=payload.second_last_name.strip() if payload.second_last_name else None,
        identity_document=document,
        analytics_id=analytics_identifier(document, email),
        phone=payload.phone.strip() if payload.phone else None,
        email=email,
        password_hash=hash_password(temporary_password),
        role=UserRole.VIEWER,
        title='SIN_ASIGNAR',
        active=payload.active,
        can_request=False,
        can_approve=False,
        can_view=False,
        can_configure=False,
        must_change_password=True,
    )
    db.add(user)
    try:
        db.flush()
        _replace_assignments(
            db,
            user,
            group_ids=payload.group_ids,
            role_ids=payload.role_ids,
            permission_codes=payload.direct_permission_codes,
            position_ids=payload.position_ids,
        )
        db.flush()
        _sync_legacy_display_fields(db, user)
        if user.active:
            positions, permissions = _access_email_summary(db, user)
            send_user_invitation(user, temporary_password, positions, permissions)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail='Ya existe un usuario con ese correo o identificación') from exc
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail='No se pudo crear e invitar al usuario') from exc
    db.refresh(user)
    return _out(db, user)


@router.patch('/{user_id}', response_model=IamUserOut)
def update_user(user_id: int, payload: IamUserUpdate, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if not user:
        raise HTTPException(status_code=404, detail='Usuario no encontrado')
    if db.scalar(select(SystemAccount.id).where(SystemAccount.user_id == user.id)):
        raise HTTPException(status_code=409, detail='La cuenta técnica se administra mediante el bootstrap de despliegue')

    previous_email = user.email
    previous_active = user.active

    original_position_ids = set(db.scalars(
        select(UserPosition.position_id).where(UserPosition.user_id == user.id)
    ).all())

    changes = payload.model_dump(
        exclude_unset=True,
        exclude={'group_ids', 'role_ids', 'direct_permission_codes', 'position_ids'},
    )
    if 'email' in changes:
        email = normalize_email(str(changes['email']))
        if db.scalar(select(User.id).where(func.lower(User.email) == email, User.id != user.id)):
            raise HTTPException(status_code=409, detail='Ya existe un usuario con ese correo')
        changes['email'] = email
    if 'identity_document' in changes:
        document = changes['identity_document'].strip().upper()
        if db.scalar(select(User.id).where(
            func.upper(func.trim(User.identity_document)) == document,
            User.id != user.id,
        )):
            raise HTTPException(status_code=409, detail='Ya existe un usuario con esa identificación')
        changes['identity_document'] = document

    for key, value in changes.items():
        if isinstance(value, str):
            value = value.strip()
        setattr(user, key, value)
    if user.email != previous_email or user.active != previous_active:
        user.password_reset_version += 1
    user.name = _full_name(user)
    if {'email', 'identity_document'} & set(changes):
        user.analytics_id = analytics_identifier(user.identity_document, user.email)

    position_changed = (
        payload.position_ids is not None
        and set(payload.position_ids) != original_position_ids
    )
    try:
        _replace_assignments(
            db,
            user,
            group_ids=payload.group_ids,
            role_ids=payload.role_ids,
            permission_codes=payload.direct_permission_codes,
            position_ids=payload.position_ids,
        )
        db.flush()
        _sync_legacy_display_fields(db, user)
        if position_changed and user.active:
            positions, permissions = _access_email_summary(db, user)
            send_user_access_updated(user, positions, permissions)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        if position_changed:
            raise HTTPException(
                status_code=502,
                detail='No se pudo actualizar el cargo y enviar la notificación al usuario',
            ) from exc
        raise
    db.refresh(user)
    return _out(db, user)
