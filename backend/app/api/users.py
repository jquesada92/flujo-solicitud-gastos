import secrets
import re
import unicodedata

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import current_user, hash_password, normalize_email, require_permission
from app.models.entities import AccessProfile, AccessProfileChangeEvent, User, UserChangeEvent, UserRole
from app.schemas.user import AccessProfileOut, AccessProfileUpdate, AccessProfileWrite, UserBulkUpdate, UserChangeEventOut, UserCreate, UserOut, UserUpdate
from app.services.email_service import send_user_invitation

router = APIRouter(dependencies=[Depends(require_permission('can_configure'))])

AUDITED_FIELDS = ('name', 'apartment_number', 'title', 'role', 'active', 'can_request', 'can_approve', 'can_view', 'can_configure', 'must_change_password')

def _snapshot(user: User) -> dict:
    return {key: (getattr(user, key).value if key == 'role' else getattr(user, key)) for key in AUDITED_FIELDS}


def _profile_snapshot(profile: AccessProfile) -> dict:
    return {key: getattr(profile, key) for key in ('name', 'can_request', 'can_approve', 'can_view', 'can_configure', 'has_user_limit', 'max_users', 'active')}


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
    base = re.sub(r'[^A-Z]+', '_', ''.join(c for c in normalized if not unicodedata.combining(c)).upper()).strip('_')[:60]
    code, sequence = base, 2
    while db.scalar(select(AccessProfile.id).where(AccessProfile.code == code)):
        code = f'{base}_{sequence}'; sequence += 1
    return code


def _ensure_title_available(db: Session, profile: AccessProfile, active: bool, except_user_id: int | None = None) -> None:
    if not active or not profile.has_user_limit:
        return
    stmt = select(func.count(User.id)).where(User.title == profile.code, User.active.is_(True))
    if except_user_id is not None:
        stmt = stmt.where(User.id != except_user_id)
    current_count = db.scalar(stmt) or 0
    if current_count >= (profile.max_users or 0):
        raise HTTPException(status_code=409, detail=f'El cargo {profile.name} alcanzó su límite de {profile.max_users} persona(s) activas')


@router.get('', response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)):
    return list(db.scalars(select(User).order_by(User.name)).all())


@router.get('/changes', response_model=list[UserChangeEventOut])
def list_user_changes(limit: int = 100, db: Session = Depends(get_db)):
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
def create_profile(payload: AccessProfileWrite, db: Session = Depends(get_db), actor: User = Depends(current_user)):
    profile = AccessProfile(code=_profile_code(db, payload.name), **payload.model_dump())
    db.add(profile); db.flush()
    after = _profile_snapshot(profile)
    db.add(AccessProfileChangeEvent(event_type='PROFILE_CREATED', profile_id=profile.id, profile_code=profile.code,
                                    actor_user_id=actor.id, actor_email=actor.email,
                                    changed_fields=list(after.keys()), before_state=None, after_state=after))
    db.commit(); db.refresh(profile)
    return profile


@router.patch('/profiles/{profile_id}', response_model=AccessProfileOut)
def update_profile(profile_id: int, payload: AccessProfileUpdate, db: Session = Depends(get_db), actor: User = Depends(current_user)):
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
        assigned = db.scalar(select(func.count(User.id)).where(User.title == profile.code, User.active.is_(True))) or 0
        if assigned > resulting_max:
            raise HTTPException(status_code=409, detail=f'El cargo tiene {assigned} persona(s) activas; el límite no puede ser menor')
    for key, value in changes.items():
        setattr(profile, key, value.strip() if key == 'name' else value)
    after = _profile_snapshot(profile)
    changed = [key for key in after if before[key] != after[key]]
    if changed:
        db.add(AccessProfileChangeEvent(event_type='PROFILE_UPDATED', profile_id=profile.id, profile_code=profile.code,
                                        actor_user_id=actor.id, actor_email=actor.email,
                                        changed_fields=changed, before_state=before, after_state=after))
        permission_fields = {'can_request', 'can_approve', 'can_view', 'can_configure'}
        if permission_fields.intersection(changed):
            for assigned_user in db.scalars(select(User).where(User.title == profile.code, User.role != UserRole.ADMIN)).all():
                user_before = _snapshot(assigned_user)
                _apply_profile_permissions(assigned_user, profile)
                user_after = _snapshot(assigned_user)
                user_changed = [key for key in AUDITED_FIELDS if user_before[key] != user_after[key]]
                if user_changed:
                    db.add(UserChangeEvent(event_type='PROFILE_PERMISSIONS_APPLIED', user_id=assigned_user.id,
                                           user_email=assigned_user.email, actor_user_id=actor.id,
                                           actor_email=actor.email, changed_fields=user_changed,
                                           before_state=user_before, after_state=user_after))
    db.commit(); db.refresh(profile)
    return profile


@router.post('', response_model=UserOut, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db), actor: User = Depends(current_user)):
    email = normalize_email(str(payload.email))
    if db.scalar(select(User.id).where(func.lower(User.email) == email)):
        raise HTTPException(status_code=409, detail='Ya existe un usuario con ese correo')
    profile = db.scalar(select(AccessProfile).where(AccessProfile.code == payload.title, AccessProfile.active.is_(True)))
    if not profile:
        raise HTTPException(status_code=422, detail='El cargo seleccionado no existe o está inactivo')
    _ensure_title_available(db, profile, True)
    temporary_password = secrets.token_urlsafe(15)
    user = User(name=payload.name.strip(), email=email, apartment_number=payload.apartment_number.strip().upper(), password_hash=hash_password(temporary_password),
                role=_role_for_permissions(profile.can_request, profile.can_approve), title=profile.code,
                can_request=profile.can_request, can_approve=profile.can_approve,
                can_view=profile.can_view, can_configure=profile.can_configure,
                must_change_password=True)
    db.add(user)
    try:
        db.flush()
        after = _snapshot(user)
        db.add(UserChangeEvent(event_type='USER_CREATED', user_id=user.id, user_email=user.email,
                               actor_user_id=actor.id, actor_email=actor.email,
                               changed_fields=list(after.keys()), before_state=None, after_state=after))
        send_user_invitation(user, temporary_password)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail='No se pudo enviar la invitación. El usuario no fue creado.') from exc
    db.refresh(user)
    return user


def _apply_user_changes(db: Session, user: User, changes: dict, actor: User) -> None:
    if user.role == UserRole.ADMIN:
        raise HTTPException(status_code=403, detail='El Administrador del sistema no puede modificarse desde esta pantalla')
    before = _snapshot(user)
    new_title = changes.get('title')
    profile = None
    if new_title:
        profile = db.scalar(select(AccessProfile).where(AccessProfile.code == new_title, AccessProfile.active.is_(True)))
        if not profile:
            raise HTTPException(status_code=422, detail='El cargo seleccionado no existe o está inactivo')
    resulting_title = new_title or user.title
    resulting_active = changes.get('active', user.active)
    target_profile = profile if new_title else db.scalar(select(AccessProfile).where(AccessProfile.code == resulting_title))
    if target_profile:
        _ensure_title_available(db, target_profile, resulting_active, user.id)
    for key, value in changes.items():
        if key in ('name', 'apartment_number') and value:
            value = value.strip().upper() if key == 'apartment_number' else value.strip()
        setattr(user, key, value)
    if target_profile:
        _apply_profile_permissions(user, target_profile)
    after = _snapshot(user)
    changed_fields = [key for key in AUDITED_FIELDS if before[key] != after[key]]
    if changed_fields:
        db.add(UserChangeEvent(event_type='USER_ACCESS_UPDATED', user_id=user.id, user_email=user.email,
                               actor_user_id=actor.id, actor_email=actor.email,
                               changed_fields=changed_fields, before_state=before, after_state=after))


@router.patch('/bulk', response_model=list[UserOut])
def bulk_update_users(payload: UserBulkUpdate, db: Session = Depends(get_db), actor: User = Depends(current_user)):
    ids = [item.id for item in payload.users]
    if len(ids) != len(set(ids)):
        raise HTTPException(status_code=422, detail='La solicitud contiene usuarios repetidos')
    records = {user.id: user for user in db.scalars(select(User).where(User.id.in_(ids)).with_for_update()).all()}
    missing = [user_id for user_id in ids if user_id not in records]
    if missing:
        raise HTTPException(status_code=404, detail=f'Usuarios no encontrados: {missing}')
    try:
        for item in payload.users:
            changes = item.model_dump(exclude={'id'}, exclude_unset=True)
            _apply_user_changes(db, records[item.id], changes, actor)
            db.flush()
        db.commit()
    except Exception:
        db.rollback()
        raise
    return list(db.scalars(select(User).order_by(User.name)).all())


@router.post('/{user_id}/regenerate-password', response_model=UserOut)
def regenerate_password(user_id: int, db: Session = Depends(get_db), actor: User = Depends(current_user)):
    user = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if not user:
        raise HTTPException(status_code=404, detail='Usuario no encontrado')
    if user.role == UserRole.ADMIN:
        raise HTTPException(status_code=403, detail='La contraseña del Administrador del sistema no puede regenerarse desde esta pantalla')
    if not user.active:
        raise HTTPException(status_code=409, detail='Activa el usuario antes de regenerar su contraseña')

    before = _snapshot(user)
    temporary_password = secrets.token_urlsafe(15)
    user.password_hash = hash_password(temporary_password)
    user.must_change_password = True
    after = _snapshot(user)
    db.add(UserChangeEvent(
        event_type='USER_PASSWORD_REGENERATED', user_id=user.id, user_email=user.email,
        actor_user_id=actor.id, actor_email=actor.email,
        changed_fields=['password_hash', 'must_change_password'],
        before_state=before, after_state=after,
    ))
    try:
        send_user_invitation(user, temporary_password)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail='No se pudo enviar la nueva contraseña. La contraseña anterior continúa vigente.') from exc
    db.refresh(user)
    return user


@router.patch('/{user_id}', response_model=UserOut)
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db), actor: User = Depends(current_user)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail='Usuario no encontrado')
    _apply_user_changes(db, user, payload.model_dump(exclude_unset=True), actor)
    db.commit()
    db.refresh(user)
    return user
