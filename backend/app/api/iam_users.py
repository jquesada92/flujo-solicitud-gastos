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
    Permission,
    Position,
    Role,
    SystemAccount,
    UserGroup,
    UserPermission,
    UserPosition,
    UserRoleAssignment,
)
from app.schemas.iam_user import IamUserCreate, IamUserOut, IamUserUpdate
from app.services.email_service import send_user_invitation
from app.services.iam_service import (
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
    direct_permissions = list(db.scalars(
        select(Permission.code)
        .join(UserPermission, UserPermission.permission_id == Permission.id)
        .where(UserPermission.user_id == user.id)
        .order_by(Permission.code)
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
        direct_permission_codes=direct_permissions,
        effective_permission_codes=sorted(effective_permission_codes(db, user.id)),
        permission_sources=permission_sources(db, user.id),
    )


def _validate_assignments(
    db: Session,
    group_ids: list[int],
    role_ids: list[int],
    permission_codes: list[str],
    position_ids: list[int],
) -> tuple[list[UserGroup], list[Role], list[Permission], list[Position]]:
    groups = list(db.scalars(select(UserGroup).where(UserGroup.id.in_(set(group_ids)), UserGroup.active.is_(True))).all()) if group_ids else []
    roles = list(db.scalars(select(Role).where(Role.id.in_(set(role_ids)), Role.active.is_(True))).all()) if role_ids else []
    permissions = list(db.scalars(select(Permission).where(Permission.code.in_(set(permission_codes)), Permission.active.is_(True))).all()) if permission_codes else []
    positions = list(db.scalars(select(Position).where(Position.id.in_(set(position_ids)), Position.active.is_(True))).all()) if position_ids else []

    if len(groups) != len(set(group_ids)):
        raise HTTPException(status_code=422, detail='Uno o más grupos no existen o están inactivos')
    if len(roles) != len(set(role_ids)):
        raise HTTPException(status_code=422, detail='Uno o más roles no existen o están inactivos')
    if any(role.system_managed for role in roles):
        raise HTTPException(status_code=422, detail='Los roles técnicos del sistema no pueden asignarse manualmente')
    if len(permissions) != len(set(permission_codes)):
        raise HTTPException(status_code=422, detail='Uno o más permisos no existen o están inactivos')
    if len(positions) != len(set(position_ids)):
        raise HTTPException(status_code=422, detail='Uno o más cargos no existen o están inactivos')
    return groups, roles, permissions, positions


def _replace_assignments(
    db: Session,
    user: User,
    *,
    group_ids: list[int] | None = None,
    role_ids: list[int] | None = None,
    permission_codes: list[str] | None = None,
    position_ids: list[int] | None = None,
) -> None:
    current_group_ids = list(db.scalars(select(GroupMember.group_id).where(GroupMember.user_id == user.id)).all())
    current_role_ids = list(db.scalars(select(UserRoleAssignment.role_id).where(UserRoleAssignment.user_id == user.id)).all())
    current_permission_codes = list(db.scalars(
        select(Permission.code)
        .join(UserPermission, UserPermission.permission_id == Permission.id)
        .where(UserPermission.user_id == user.id)
    ).all())
    current_position_ids = list(db.scalars(select(UserPosition.position_id).where(UserPosition.user_id == user.id)).all())

    target_group_ids = current_group_ids if group_ids is None else list(dict.fromkeys(group_ids))
    target_role_ids = current_role_ids if role_ids is None else list(dict.fromkeys(role_ids))
    target_permission_codes = current_permission_codes if permission_codes is None else list(dict.fromkeys(permission_codes))
    target_position_ids = current_position_ids if position_ids is None else list(dict.fromkeys(position_ids))

    groups, roles, permissions, positions = _validate_assignments(
        db,
        target_group_ids,
        target_role_ids,
        target_permission_codes,
        target_position_ids,
    )

    if group_ids is not None:
        db.execute(delete(GroupMember).where(GroupMember.user_id == user.id))
        db.add_all(GroupMember(user_id=user.id, group_id=item.id) for item in groups)
    if role_ids is not None:
        db.execute(delete(UserRoleAssignment).where(UserRoleAssignment.user_id == user.id))
        db.add_all(UserRoleAssignment(user_id=user.id, role_id=item.id) for item in roles)
    if permission_codes is not None:
        db.execute(delete(UserPermission).where(UserPermission.user_id == user.id))
        db.add_all(UserPermission(user_id=user.id, permission_id=item.id) for item in permissions)
    if position_ids is not None:
        db.execute(delete(UserPosition).where(UserPosition.user_id == user.id))
        db.add_all(UserPosition(user_id=user.id, position_id=item.id) for item in positions)


def _sync_legacy_display_fields(db: Session, user: User) -> None:
    """Mirror IAM into old fields so the legacy React screen remains readable.

    These fields are compatibility output only; authorization never reads them.
    """
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
def list_users(db: Session = Depends(get_db)):
    return [_out(db, user) for user in db.scalars(select(User).order_by(User.name)).all()]


@router.post('', response_model=IamUserOut, status_code=201)
def create_user(payload: IamUserCreate, db: Session = Depends(get_db)):
    email = normalize_email(str(payload.email))
    document = payload.identity_document.strip().upper()
    if db.scalar(select(User.id).where(func.lower(User.email) == email)):
        raise HTTPException(status_code=409, detail='Ya existe un usuario con ese correo')
    if db.scalar(select(User.id).where(func.upper(func.trim(User.identity_document)) == document)):
        raise HTTPException(status_code=409, detail='Ya existe un usuario con esa identificación')

    _validate_assignments(
        db,
        payload.group_ids,
        payload.role_ids,
        payload.direct_permission_codes,
        payload.position_ids,
    )
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
            send_user_invitation(user, temporary_password)
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
    user.name = _full_name(user)
    if {'email', 'identity_document'} & set(changes):
        user.analytics_id = analytics_identifier(user.identity_document, user.email)

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
    db.commit()
    db.refresh(user)
    return _out(db, user)
