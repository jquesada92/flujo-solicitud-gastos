import re
import secrets
import unicodedata

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.privacy import analytics_identifier, can_view_personal_data, mask_email, mask_tail
from app.core.security import create_password_reset_token, current_user, hash_password, normalize_email
from app.models.entities import AccessProfile, AccessProfileChangeEvent, User, UserChangeEvent, UserRole
from app.models.iam import Role, SystemAccount, UserRoleAssignment
from app.schemas.user import AccessProfileOut, AccessProfileUpdate, AccessProfileWrite, BoardAssignmentUpdate, UserBulkUpdate, UserChangeEventOut, UserCreate, UserOut, UserUpdate
from app.services.email_service import send_password_reset_link, send_user_invitation
from app.services.iam_service import active_role_assignment_count


BOARD_CODES = {'PRESIDENTE', 'VICEPRESIDENTE', 'TESORERO', 'VOCERO'}
ALLOWED_ACCESS_CODES = {*BOARD_CODES, 'ADMINISTRADORA'}
AUDITED_FIELDS = (
    'name', 'analytics_id', 'identity_document', 'email', 'phone', 'title', 'role',
    'active', 'can_request', 'can_approve', 'can_view', 'can_configure',
    'must_change_password',
)


def require_people_access(user: User = Depends(current_user)) -> User:
    if (
        user.role != UserRole.ADMIN
        and user.title not in BOARD_CODES
        and user.title != 'ADMINISTRADORA'
        and not user.can_configure
    ):
        raise HTTPException(status_code=403, detail='No tienes acceso a la administración de personas')
    return user


def require_system_configuration(user: User = Depends(current_user)) -> User:
    if user.role != UserRole.ADMIN and not user.can_configure:
        raise HTTPException(status_code=403, detail='Esta acción está reservada al Administrador del sistema')
    return user


def require_people_write(user: User = Depends(current_user)) -> User:
    if user.role != UserRole.ADMIN and user.title != 'ADMINISTRADORA' and not user.can_configure:
        raise HTTPException(status_code=403, detail='Tienes acceso de solo lectura')
    return user


router = APIRouter(dependencies=[Depends(require_people_access)])


def _snapshot(user: User) -> dict:
    snapshot = {
        key: (value.value if hasattr((value := getattr(user, key)), 'value') else value)
        for key in AUDITED_FIELDS
    }
    snapshot['identity_document'] = mask_tail(snapshot.get('identity_document'))
    snapshot['email'] = mask_email(snapshot.get('email'))
    snapshot['phone'] = mask_tail(snapshot.get('phone'))
    return snapshot


def _audit_email(value: str) -> str:
    return mask_email(value) or '***'


def _profile_snapshot(profile: AccessProfile) -> dict:
    return {
        key: getattr(profile, key)
        for key in (
            'name', 'can_request', 'can_approve', 'can_view', 'can_configure',
            'has_user_limit', 'max_users', 'active',
        )
    }


def _role_for_permissions(can_request: bool, can_approve: bool) -> UserRole:
    return UserRole.APPROVER if can_approve else UserRole.REQUESTER if can_request else UserRole.VIEWER


def _apply_profile_permissions(user: User, profile: AccessProfile) -> None:
    user.title = profile.code
    user.can_request = profile.can_request
    user.can_approve = profile.can_approve
    user.can_view = profile.can_view
    user.can_configure = profile.can_configure
    user.role = _role_for_permissions(profile.can_request, profile.can_approve)


def _profile_code(db: Session, name: str) -> str:
    normalized = unicodedata.normalize('NFKD', name)
    base = re.sub(
        r'[^A-Z]+', '_',
        ''.join(c for c in normalized if not unicodedata.combining(c)).upper(),
    ).strip('_')[:60]
    code, sequence = base, 2
    while db.scalar(select(AccessProfile.id).where(AccessProfile.code == code)):
        code = f'{base}_{sequence}'
        sequence += 1
    return code


def _ensure_title_available(
    db: Session,
    profile: AccessProfile,
    active: bool,
    except_user_id: int | None = None,
) -> None:
    if not active or not profile.has_user_limit:
        return
    stmt = select(func.count(User.id)).where(User.title == profile.code, User.active.is_(True))
    if except_user_id is not None:
        stmt = stmt.where(User.id != except_user_id)
    current_count = db.scalar(stmt) or 0
    if current_count >= (profile.max_users or 0):
        raise HTTPException(
            status_code=409,
            detail=f'El cargo {profile.name} alcanzó su límite de {profile.max_users} persona(s) activas',
        )


@router.get('', response_model=list[UserOut])
def list_users(include_inactive: bool = False, db: Session = Depends(get_db), viewer: User = Depends(current_user)):
    stmt = select(User).order_by(User.name)
    if not include_inactive:
        stmt = stmt.where(User.active.is_(True))
    users = list(db.scalars(stmt).all())
    if can_view_personal_data(viewer):
        return users
    output = []
    for user in users:
        data = UserOut.model_validate(user).model_dump()
        if user.id != viewer.id:
            data['identity_document'] = mask_tail(data['identity_document'])
            data['phone'] = mask_tail(data['phone'])
            data['email'] = mask_email(data['email'])
        output.append(data)
    return output


@router.get('/search', response_model=list[UserOut])
def search_users(
    q: str,
    limit: int = 10,
    db: Session = Depends(get_db),
    viewer: User = Depends(require_people_write),
):
    query = q.strip()
    if len(query) < 2:
        raise HTTPException(status_code=422, detail='Escribe al menos 2 caracteres para buscar')
    pattern = f'%{query}%'
    stmt = (
        select(User)
        .where(
            User.role != UserRole.ADMIN,
            (User.name.ilike(pattern))
            | (User.first_name.ilike(pattern))
            | (User.middle_name.ilike(pattern))
            | (User.last_name.ilike(pattern))
            | (User.second_last_name.ilike(pattern))
            | (User.identity_document.ilike(pattern))
            | (User.email.ilike(pattern)),
        )
        .order_by(User.name)
        .limit(min(max(limit, 1), 20))
    )
    return list(db.scalars(stmt).all())


@router.get('/recovery', response_model=UserOut | None)
def recover_user(
    identity_document: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_people_write),
):
    document = identity_document.strip().upper()
    user = db.scalar(select(User).where(
        func.upper(func.trim(User.identity_document)) == document,
        User.active.is_(False),
        User.role != UserRole.ADMIN,
    ))
    return user


@router.get('/changes', response_model=list[UserChangeEventOut])
def list_user_changes(
    limit: int = 100,
    db: Session = Depends(get_db),
    _: User = Depends(require_system_configuration),
):
    safe_limit = min(max(limit, 1), 500)
    month_start = func.date_trunc('month', func.now())
    stmt = (
        select(UserChangeEvent)
        .where(
            UserChangeEvent.occurred_at >= month_start,
            UserChangeEvent.occurred_at < month_start + text("INTERVAL '1 month'"),
        )
        .order_by(UserChangeEvent.event_sequence.desc())
        .limit(safe_limit)
    )
    return list(db.scalars(stmt).all())


@router.get('/profiles', response_model=list[AccessProfileOut])
def list_profiles(include_inactive: bool = False, db: Session = Depends(get_db)):
    stmt = select(AccessProfile).order_by(AccessProfile.name)
    if not include_inactive:
        stmt = stmt.where(AccessProfile.active.is_(True))
    return list(db.scalars(stmt).all())


@router.post('/profiles', response_model=AccessProfileOut, status_code=201)
def create_profile(
    payload: AccessProfileWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_system_configuration),
):
    code = _profile_code(db, payload.name)
    profile = AccessProfile(code=code, **payload.model_dump())
    db.add(profile)
    db.flush()
    after = _profile_snapshot(profile)
    db.add(AccessProfileChangeEvent(
        event_type='PROFILE_CREATED', profile_id=profile.id, profile_code=profile.code,
        actor_user_id=actor.id, actor_email=_audit_email(actor.email),
        changed_fields=list(after.keys()), before_state=None, after_state=after,
    ))
    db.commit()
    db.refresh(profile)
    return profile


@router.patch('/profiles/{profile_id}', response_model=AccessProfileOut)
def update_profile(
    profile_id: int,
    payload: AccessProfileUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_system_configuration),
):
    profile = db.get(AccessProfile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail='Cargo no encontrado')
    before = _profile_snapshot(profile)
    changes = payload.model_dump(exclude_unset=True)
    resulting_has_limit = changes.get('has_user_limit', profile.has_user_limit)
    resulting_max = changes.get('max_users', profile.max_users)
    if resulting_has_limit and resulting_max is None:
        raise HTTPException(status_code=422, detail='Debes indicar el número máximo de personas')
    if not resulting_has_limit:
        changes['max_users'] = None
    if resulting_has_limit:
        assigned = db.scalar(
            select(func.count(User.id)).where(User.title == profile.code, User.active.is_(True))
        ) or 0
        if assigned > resulting_max:
            raise HTTPException(
                status_code=409,
                detail=f'El cargo tiene {assigned} persona(s) activas; el límite no puede ser menor',
            )
    for key, value in changes.items():
        setattr(profile, key, value.strip() if key == 'name' else value)
    after = _profile_snapshot(profile)
    changed = [key for key in after if before[key] != after[key]]
    if changed:
        db.add(AccessProfileChangeEvent(
            event_type='PROFILE_UPDATED', profile_id=profile.id, profile_code=profile.code,
            actor_user_id=actor.id, actor_email=_audit_email(actor.email),
            changed_fields=changed, before_state=before, after_state=after,
        ))
        permission_fields = {'can_request', 'can_approve', 'can_view', 'can_configure'}
        if permission_fields.intersection(changed):
            assigned_users = db.scalars(
                select(User).where(User.title == profile.code, User.role != UserRole.ADMIN)
            ).all()
            for assigned_user in assigned_users:
                user_before = _snapshot(assigned_user)
                _apply_profile_permissions(assigned_user, profile)
                user_after = _snapshot(assigned_user)
                user_changed = [key for key in AUDITED_FIELDS if user_before[key] != user_after[key]]
                if user_changed:
                    db.add(UserChangeEvent(
                        event_type='PROFILE_PERMISSIONS_APPLIED', user_id=assigned_user.id,
                        user_email=_audit_email(assigned_user.email), actor_user_id=actor.id,
                        actor_email=_audit_email(actor.email), changed_fields=user_changed,
                        before_state=user_before, after_state=user_after,
                    ))
    db.commit()
    db.refresh(profile)
    return profile


@router.post('', response_model=UserOut, status_code=201)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_people_write),
):
    email = normalize_email(str(payload.email))
    if db.scalar(select(User.id).where(func.lower(User.email) == email)):
        raise HTTPException(status_code=409, detail='Ya existe un usuario con ese correo')
    document = payload.identity_document.strip().upper()
    if db.scalar(select(User.id).where(func.upper(func.trim(User.identity_document)) == document)):
        raise HTTPException(status_code=409, detail='Ya existe un usuario con esa cédula o pasaporte')
    profile = db.scalar(select(AccessProfile).where(
        AccessProfile.code == payload.title,
        AccessProfile.active.is_(True),
    ))
    if not profile or profile.code not in ALLOWED_ACCESS_CODES:
        raise HTTPException(status_code=422, detail='El cargo seleccionado no existe o está inactivo')
    _ensure_title_available(db, profile, payload.active)
    temporary_password = secrets.token_urlsafe(15)
    name_parts = [payload.first_name, payload.middle_name, payload.last_name, payload.second_last_name]
    full_name = ' '.join(part.strip() for part in name_parts if part and part.strip())
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
        role=_role_for_permissions(profile.can_request, profile.can_approve),
        title=profile.code,
        active=payload.active,
        can_request=profile.can_request,
        can_approve=profile.can_approve,
        can_view=profile.can_view,
        can_configure=profile.can_configure,
        must_change_password=True,
    )
    db.add(user)
    try:
        db.flush()
        after = _snapshot(user)
        db.add(UserChangeEvent(
            event_type='USER_CREATED', user_id=user.id, user_email=_audit_email(user.email),
            actor_user_id=actor.id, actor_email=_audit_email(actor.email),
            changed_fields=list(after.keys()), before_state=None, after_state=after,
        ))
        if user.active:
            send_user_invitation(user, temporary_password)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail='Ya existe un usuario con ese correo o cédula') from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=502,
            detail='No se pudo enviar la invitación. El usuario no fue creado.',
        ) from exc
    db.refresh(user)
    return user


def _apply_user_changes(db: Session, user: User, changes: dict, actor: User) -> None:
    if user.role == UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail='El Administrador del sistema no puede modificarse desde esta pantalla',
        )
    before = _snapshot(user)
    previous_email = user.email
    previous_active = user.active
    if changes.get('active') is True and not user.active:
        assigned_role_ids = select(UserRoleAssignment.role_id).where(
            UserRoleAssignment.user_id == user.id
        )
        assigned_roles = list(db.scalars(
            select(Role)
            .where(Role.id.in_(assigned_role_ids))
            .order_by(Role.id)
            .with_for_update()
        ).all())
        for role in assigned_roles:
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
    if 'email' in changes:
        email = normalize_email(str(changes['email']))
        duplicate = db.scalar(
            select(User.id).where(func.lower(User.email) == email, User.id != user.id)
        )
        if duplicate:
            raise HTTPException(status_code=409, detail='Ya existe un usuario con ese correo')
        changes['email'] = email
    if 'identity_document' in changes:
        document = changes['identity_document'].strip().upper()
        duplicate = db.scalar(
            select(User.id).where(
                func.upper(func.trim(User.identity_document)) == document,
                User.id != user.id,
            )
        )
        if duplicate:
            raise HTTPException(status_code=409, detail='Ya existe un usuario con esa cédula o pasaporte')
        changes['identity_document'] = document

    new_title = changes.get('title')
    profile = None
    if new_title and new_title != 'SIN_ASIGNAR':
        profile = db.scalar(select(AccessProfile).where(
            AccessProfile.code == new_title,
            AccessProfile.active.is_(True),
        ))
        if not profile or profile.code not in ALLOWED_ACCESS_CODES:
            raise HTTPException(status_code=422, detail='El cargo seleccionado no existe o está inactivo')

    resulting_title = new_title or user.title
    resulting_active = changes.get('active', user.active)
    target_profile = profile if new_title else db.scalar(
        select(AccessProfile).where(AccessProfile.code == resulting_title)
    )
    if target_profile:
        _ensure_title_available(db, target_profile, resulting_active, user.id)

    for key, value in changes.items():
        if key in ('name', 'first_name', 'middle_name', 'last_name', 'second_last_name', 'phone') and value:
            value = value.strip()
        setattr(user, key, value)

    if user.email != previous_email or user.active != previous_active:
        user.password_reset_version += 1

    personal_name_fields = {'first_name', 'middle_name', 'last_name', 'second_last_name'}
    if personal_name_fields.intersection(changes):
        user.name = ' '.join(
            part for part in (user.first_name, user.middle_name, user.last_name, user.second_last_name)
            if part
        )
    if {'identity_document', 'email'}.intersection(changes):
        user.analytics_id = analytics_identifier(user.identity_document, user.email)
    if target_profile:
        _apply_profile_permissions(user, target_profile)
    elif resulting_title == 'SIN_ASIGNAR':
        user.role = UserRole.VIEWER
        user.can_request = False
        user.can_approve = False
        user.can_view = False
        user.can_configure = False

    after = _snapshot(user)
    changed_fields = [key for key in after if before[key] != after[key]]
    if changed_fields:
        db.add(UserChangeEvent(
            event_type='USER_ACCESS_UPDATED', user_id=user.id,
            user_email=_audit_email(user.email), actor_user_id=actor.id,
            actor_email=_audit_email(actor.email), changed_fields=changed_fields,
            before_state=before, after_state=after,
        ))


@router.patch('/bulk', response_model=list[UserOut])
def bulk_update_users(
    payload: UserBulkUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_system_configuration),
):
    ids = [item.id for item in payload.users]
    if len(ids) != len(set(ids)):
        raise HTTPException(status_code=422, detail='La solicitud contiene usuarios repetidos')
    records = {
        user.id: user
        for user in db.scalars(select(User).where(User.id.in_(ids)).with_for_update()).all()
    }
    missing = [user_id for user_id in ids if user_id not in records]
    if missing:
        raise HTTPException(status_code=404, detail=f'Usuarios no encontrados: {missing}')
    try:
        for item in payload.users:
            changes = item.model_dump(exclude={'id'}, exclude_unset=True)
            _apply_user_changes(db, records[item.id], changes, actor)
            db.flush()
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail='Ya existe un usuario con ese correo o cédula') from exc
    except Exception:
        db.rollback()
        raise
    return list(db.scalars(select(User).order_by(User.name)).all())


@router.patch('/board', response_model=list[UserOut])
def update_board(
    payload: BoardAssignmentUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_system_configuration),
):
    assignments = {
        'PRESIDENTE': [payload.president_id] if payload.president_id else [],
        'VICEPRESIDENTE': [payload.vice_president_id] if payload.vice_president_id else [],
        'TESORERO': [payload.treasurer_id] if payload.treasurer_id else [],
        'VOCERO': payload.vocal_ids,
    }
    selected_ids = {user_id for ids in assignments.values() for user_id in ids}
    selected = {
        user.id: user
        for user in db.scalars(
            select(User).where(User.id.in_(selected_ids)).with_for_update()
        ).all()
    } if selected_ids else {}
    if set(selected) != selected_ids or any(
        not user.active or user.role == UserRole.ADMIN for user in selected.values()
    ):
        raise HTTPException(
            status_code=422,
            detail='El nivel directivo solo puede incluir usuarios activos del sistema',
        )
    profiles = {
        item.code: item
        for item in db.scalars(
            select(AccessProfile).where(AccessProfile.code.in_(assignments))
        ).all()
    }
    if len(profiles) != 4:
        raise HTTPException(
            status_code=422,
            detail='Faltan perfiles requeridos para configurar el organigrama directivo',
        )
    current = list(db.scalars(
        select(User).where(User.title.in_(assignments)).with_for_update()
    ).all())
    try:
        for user in current:
            if user.id not in selected_ids:
                _apply_user_changes(db, user, {'title': 'SIN_ASIGNAR'}, actor)
        db.flush()
        for code, ids in assignments.items():
            for user_id in ids:
                _apply_user_changes(db, selected[user_id], {'title': code}, actor)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return list(db.scalars(
        select(User).where(User.title.in_(assignments)).order_by(User.title, User.name)
    ).all())


@router.post('/{user_id}/regenerate-password', response_model=UserOut)
def regenerate_password(
    user_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_system_configuration),
):
    user = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if not user:
        raise HTTPException(status_code=404, detail='Usuario no encontrado')
    if db.scalar(select(SystemAccount.id).where(SystemAccount.user_id == user.id)):
        raise HTTPException(
            status_code=403,
            detail='La contraseña del Administrador del sistema no puede restablecerse desde esta pantalla',
        )
    if not user.active:
        raise HTTPException(status_code=409, detail='Activa el usuario antes de enviar un enlace de restablecimiento')

    previous_reset_version = user.password_reset_version
    user.password_reset_version += 1
    reset_token = create_password_reset_token(user)
    db.add(UserChangeEvent(
        event_type='USER_PASSWORD_RESET_LINK_ISSUED', user_id=user.id,
        user_email=_audit_email(user.email), actor_user_id=actor.id,
        actor_email=_audit_email(actor.email),
        changed_fields=['password_reset_link'],
        before_state={'password_reset_version': previous_reset_version},
        after_state={'password_reset_version': user.password_reset_version},
    ))
    try:
        send_password_reset_link(user, reset_token)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=502,
            detail='No se pudo enviar el enlace. La contraseña y las sesiones actuales continúan vigentes.',
        ) from exc
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(user)
    return user


@router.patch('/{user_id}', response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_people_write),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail='Usuario no encontrado')
    _apply_user_changes(db, user, payload.model_dump(exclude_unset=True), actor)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail='Ya existe un usuario con ese correo o cédula') from exc
    db.refresh(user)
    return user
