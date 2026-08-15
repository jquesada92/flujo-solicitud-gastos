import secrets
import re
import unicodedata

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.privacy import analytics_identifier, can_view_personal_data, mask_email, mask_tail
from app.core.security import current_user, hash_password, normalize_email, require_permission
from app.models.entities import AccessProfile, AccessProfileChangeEvent, Apartment, ApartmentChangeEvent, OwnershipRole, PersonType, User, UserApartment, UserChangeEvent, UserRole
from app.schemas.user import ApartmentOut, ApartmentUpdate, AccessProfileOut, AccessProfileUpdate, AccessProfileWrite, BoardAssignmentUpdate, UserBulkUpdate, UserChangeEventOut, UserCreate, UserOut, UserUpdate
from app.services.email_service import send_user_invitation

def require_people_access(user: User = Depends(current_user)) -> User:
    board_codes = {'PRESIDENTE', 'VICEPRESIDENTE', 'TESORERO', 'VOCERO'}
    if user.role != UserRole.ADMIN and user.person_type != PersonType.ADMINISTRATOR and user.title not in board_codes and not user.can_configure:
        raise HTTPException(status_code=403, detail='No tienes acceso a la administración de personas')
    return user


def require_system_configuration(user: User = Depends(current_user)) -> User:
    if user.role != UserRole.ADMIN and not user.can_configure:
        raise HTTPException(status_code=403, detail='Esta acción está reservada al Administrador del sistema')
    return user


def require_people_write(user: User = Depends(current_user)) -> User:
    if user.role != UserRole.ADMIN and user.person_type != PersonType.ADMINISTRATOR:
        raise HTTPException(status_code=403, detail='Tienes acceso de solo lectura')
    return user


router = APIRouter(dependencies=[Depends(require_people_access)])
BOARD_CODES = {'PRESIDENTE', 'VICEPRESIDENTE', 'TESORERO', 'VOCERO'}
ALLOWED_ACCESS_CODES = {*BOARD_CODES, 'ADMINISTRADORA'}

AUDITED_FIELDS = ('name', 'analytics_id', 'identity_document', 'email', 'phone', 'person_type', 'apartment_number', 'title', 'role', 'active', 'can_request', 'can_approve', 'can_view', 'can_configure', 'must_change_password')


def _snapshot(user: User) -> dict:
    snapshot = {key: (value.value if hasattr((value := getattr(user, key)), 'value') else value) for key in AUDITED_FIELDS}
    snapshot['identity_document'] = mask_tail(snapshot.get('identity_document'))
    snapshot['email'] = mask_email(snapshot.get('email'))
    snapshot['phone'] = mask_tail(snapshot.get('phone'))
    snapshot['apartments'] = [
        {'apartment_number': item.apartment_number, 'ownership_role': item.ownership_role.value}
        for item in user.apartments
    ]
    return snapshot


def _audit_email(value: str) -> str:
    return mask_email(value) or '***'


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
def list_users(db: Session = Depends(get_db), viewer: User = Depends(current_user)):
    users = list(db.scalars(select(User).order_by(User.name)).all())
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
def search_users(q: str, limit: int = 10, db: Session = Depends(get_db), viewer: User = Depends(require_people_write)):
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


@router.get('/changes', response_model=list[UserChangeEventOut])
def list_user_changes(limit: int = 100, db: Session = Depends(get_db), _: User = Depends(require_system_configuration)):
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


@router.get('/apartments', response_model=list[ApartmentOut])
def list_apartments(db: Session = Depends(get_db), viewer: User = Depends(current_user)):
    apartments = db.scalars(
        select(Apartment).options(selectinload(Apartment.assignments).selectinload(UserApartment.user))
        .order_by(Apartment.floor, Apartment.letter)
    ).all()
    return [
        {
            'apartment_number': apartment.apartment_number,
            'floor': apartment.floor,
            'letter': apartment.letter,
            'is_rental': apartment.is_rental,
            'residents': [
                {'identity_document': item.user.identity_document if can_view_personal_data(viewer) else mask_tail(item.user.identity_document),
                 'full_name': item.user.full_name,
                 'email': item.user.email if can_view_personal_data(viewer) or item.user.id == viewer.id else mask_email(item.user.email),
                 'ownership_role': item.ownership_role}
                for item in apartment.assignments
            ],
        }
        for apartment in apartments
    ]


@router.patch('/apartments/{apartment_number}', response_model=ApartmentOut)
def update_apartment(apartment_number: str, payload: ApartmentUpdate,
                     db: Session = Depends(get_db), actor: User = Depends(require_people_write)):
    apartment = db.get(Apartment, apartment_number.upper())
    if not apartment:
        raise HTTPException(status_code=404, detail='Apartamento no encontrado')
    before = {'is_rental': apartment.is_rental,
              'residents': [{'identity_document': mask_tail(item.user.identity_document), 'ownership_role': item.ownership_role.value} for item in apartment.assignments]}
    if payload.is_rental is not None:
        apartment.is_rental = payload.is_rental
    requested = [(payload.owner_identity_document, OwnershipRole.OWNER), (payload.co_owner_identity_document, OwnershipRole.CO_OWNER)]
    assignments_supplied = bool({'owner_identity_document', 'co_owner_identity_document'} & payload.model_fields_set)
    if assignments_supplied:
        documents = [document.strip().upper() for document, _ in requested if document]
        if len(documents) != len(set(documents)):
            raise HTTPException(status_code=422, detail='Propietario y co-propietario deben ser personas distintas')
        selected_users = {user.identity_document: user for user in db.scalars(select(User).where(
            User.identity_document.in_(documents), User.active.is_(True),
            User.person_type.in_([PersonType.OWNER, PersonType.CO_OWNER]))).all()} if documents else {}
        if set(selected_users) != set(documents):
            raise HTTPException(status_code=422, detail='Selecciona propietarios activos válidos')
        db.query(UserApartment).filter(UserApartment.apartment_number == apartment.apartment_number).delete(synchronize_session=False)
        for document, ownership_role in requested:
            if document:
                normalized_document = document.strip().upper()
                db.add(UserApartment(user_id=selected_users[normalized_document].id, apartment_number=apartment.apartment_number,
                                     ownership_role=ownership_role))
        db.flush()
    after = {'is_rental': apartment.is_rental,
             'residents': [{'identity_document': mask_tail(document.strip().upper()), 'ownership_role': role.value} for document, role in requested if document]
             if assignments_supplied else before['residents']}
    if before != after:
        db.add(ApartmentChangeEvent(apartment_number=apartment.apartment_number,
                                    actor_user_id=actor.id, actor_email=_audit_email(actor.email),
                                    before_state=before, after_state=after))
    db.commit()
    db.expire_all()
    return list_apartments(db, actor)[(apartment.floor - 6) * 8 + ord(apartment.letter) - ord('A')]


@router.post('/profiles', response_model=AccessProfileOut, status_code=201)
def create_profile(payload: AccessProfileWrite, db: Session = Depends(get_db), actor: User = Depends(require_system_configuration)):
    code = _profile_code(db, payload.name)
    profile = AccessProfile(code=code, **payload.model_dump())
    db.add(profile); db.flush()
    after = _profile_snapshot(profile)
    db.add(AccessProfileChangeEvent(event_type='PROFILE_CREATED', profile_id=profile.id, profile_code=profile.code,
                                    actor_user_id=actor.id, actor_email=_audit_email(actor.email),
                                    changed_fields=list(after.keys()), before_state=None, after_state=after))
    db.commit(); db.refresh(profile)
    return profile


@router.patch('/profiles/{profile_id}', response_model=AccessProfileOut)
def update_profile(profile_id: int, payload: AccessProfileUpdate, db: Session = Depends(get_db), actor: User = Depends(require_system_configuration)):
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
                                        actor_user_id=actor.id, actor_email=_audit_email(actor.email),
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
                                           user_email=_audit_email(assigned_user.email), actor_user_id=actor.id,
                                           actor_email=_audit_email(actor.email), changed_fields=user_changed,
                                           before_state=user_before, after_state=user_after))
    db.commit(); db.refresh(profile)
    return profile


@router.post('', response_model=UserOut, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db), actor: User = Depends(require_people_write)):
    email = normalize_email(str(payload.email))
    if db.scalar(select(User.id).where(func.lower(User.email) == email)):
        raise HTTPException(status_code=409, detail='Ya existe un usuario con ese correo')
    document = payload.identity_document.strip().upper()
    if db.scalar(select(User.id).where(func.upper(func.trim(User.identity_document)) == document)):
        raise HTTPException(status_code=409, detail='Ya existe un usuario con esa cédula o pasaporte')
    profile = db.scalar(select(AccessProfile).where(
        AccessProfile.code == payload.title, AccessProfile.active.is_(True)))
    if not profile or profile.code not in ALLOWED_ACCESS_CODES:
        raise HTTPException(status_code=422, detail='El cargo seleccionado no existe o está inactivo')
    _ensure_title_available(db, profile, payload.active)
    temporary_password = secrets.token_urlsafe(15)
    name_parts = [payload.first_name, payload.middle_name, payload.last_name, payload.second_last_name]
    full_name = ' '.join(part.strip() for part in name_parts if part and part.strip())
    user = User(name=full_name, first_name=payload.first_name.strip(),
                middle_name=payload.middle_name.strip() if payload.middle_name else None,
                last_name=payload.last_name.strip(),
                second_last_name=payload.second_last_name.strip() if payload.second_last_name else None,
                identity_document=document, analytics_id=analytics_identifier(document, email),
                phone=payload.phone.strip() if payload.phone else None, person_type=None,
                email=email, apartment_number=None, password_hash=hash_password(temporary_password),
                role=_role_for_permissions(profile.can_request, profile.can_approve), title=profile.code,
                active=payload.active,
                can_request=profile.can_request, can_approve=profile.can_approve,
                can_view=profile.can_view, can_configure=profile.can_configure,
                must_change_password=True)
    db.add(user)
    try:
        db.flush()
        after = _snapshot(user)
        db.add(UserChangeEvent(event_type='USER_CREATED', user_id=user.id, user_email=_audit_email(user.email),
                               actor_user_id=actor.id, actor_email=_audit_email(actor.email),
                               changed_fields=list(after.keys()), before_state=None, after_state=after))
        if user.active:
            send_user_invitation(user, temporary_password)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail='Ya existe un usuario con ese correo o cédula') from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail='No se pudo enviar la invitación. El usuario no fue creado.') from exc
    db.refresh(user)
    return user


def _apply_user_changes(db: Session, user: User, changes: dict, actor: User) -> None:
    if user.role == UserRole.ADMIN:
        raise HTTPException(status_code=403, detail='El Administrador del sistema no puede modificarse desde esta pantalla')
    before = _snapshot(user)
    apartment_changes = changes.pop('apartments', None)
    if 'email' in changes:
        email = normalize_email(str(changes['email']))
        duplicate = db.scalar(select(User.id).where(func.lower(User.email) == email, User.id != user.id))
        if duplicate:
            raise HTTPException(status_code=409, detail='Ya existe un usuario con ese correo')
        changes['email'] = email
    if 'identity_document' in changes:
        document = changes['identity_document'].strip().upper()
        duplicate = db.scalar(select(User.id).where(func.upper(func.trim(User.identity_document)) == document, User.id != user.id))
        if duplicate:
            raise HTTPException(status_code=409, detail='Ya existe un usuario con esa cédula o pasaporte')
        changes['identity_document'] = document
    new_title = changes.get('title')
    profile = None
    if new_title and new_title != 'SIN_ASIGNAR':
        profile = db.scalar(select(AccessProfile).where(AccessProfile.code == new_title, AccessProfile.active.is_(True)))
        if not profile or profile.code not in ALLOWED_ACCESS_CODES:
            raise HTTPException(status_code=422, detail='El cargo seleccionado no existe o está inactivo')
    resulting_title = new_title or user.title
    resulting_active = changes.get('active', user.active)
    target_profile = profile if new_title else db.scalar(select(AccessProfile).where(AccessProfile.code == resulting_title))
    if target_profile:
        _ensure_title_available(db, target_profile, resulting_active, user.id)
    for key, value in changes.items():
        if key in ('name', 'first_name', 'middle_name', 'last_name', 'second_last_name', 'phone', 'apartment_number') and value:
            value = value.strip().upper() if key == 'apartment_number' else value.strip()
        setattr(user, key, value)
    personal_name_fields = {'first_name', 'middle_name', 'last_name', 'second_last_name'}
    if personal_name_fields.intersection(changes):
        user.name = ' '.join(part for part in (user.first_name, user.middle_name, user.last_name, user.second_last_name) if part)
    if {'identity_document', 'email'}.intersection(changes):
        user.analytics_id = analytics_identifier(user.identity_document, user.email)
    if apartment_changes is not None:
        user.apartments = [UserApartment(**item) for item in apartment_changes]
        user.apartment_number = apartment_changes[0]['apartment_number']
    if target_profile:
        _apply_profile_permissions(user, target_profile)
    elif resulting_title == 'SIN_ASIGNAR':
        user.role = UserRole.VIEWER
        user.can_request = user.can_approve = user.can_view = user.can_configure = False
    after = _snapshot(user)
    changed_fields = [key for key in after if before[key] != after[key]]
    if changed_fields:
        db.add(UserChangeEvent(event_type='USER_ACCESS_UPDATED', user_id=user.id, user_email=_audit_email(user.email),
                               actor_user_id=actor.id, actor_email=_audit_email(actor.email),
                               changed_fields=changed_fields, before_state=before, after_state=after))


@router.patch('/bulk', response_model=list[UserOut])
def bulk_update_users(payload: UserBulkUpdate, db: Session = Depends(get_db), actor: User = Depends(require_system_configuration)):
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
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail='Ya existe un usuario con ese correo o cédula') from exc
    except Exception:
        db.rollback()
        raise
    return list(db.scalars(select(User).order_by(User.name)).all())


@router.patch('/board', response_model=list[UserOut])
def update_board(payload: BoardAssignmentUpdate, db: Session = Depends(get_db), actor: User = Depends(require_system_configuration)):
    assignments = {
        'PRESIDENTE': [payload.president_id] if payload.president_id else [],
        'VICEPRESIDENTE': [payload.vice_president_id] if payload.vice_president_id else [],
        'TESORERO': [payload.treasurer_id] if payload.treasurer_id else [],
        'VOCERO': payload.vocal_ids,
    }
    selected_ids = {user_id for ids in assignments.values() for user_id in ids}
    selected = {user.id: user for user in db.scalars(select(User).where(User.id.in_(selected_ids)).with_for_update()).all()} if selected_ids else {}
    if set(selected) != selected_ids or any(not user.active or user.role == UserRole.ADMIN for user in selected.values()):
        raise HTTPException(status_code=422, detail='El nivel directivo solo puede incluir usuarios activos del sistema')
    profiles = {item.code: item for item in db.scalars(select(AccessProfile).where(AccessProfile.code.in_(assignments))).all()}
    if len(profiles) != 4:
        raise HTTPException(status_code=422, detail='Faltan perfiles requeridos para configurar el organigrama directivo')
    current = list(db.scalars(select(User).where(User.title.in_(assignments)).with_for_update()).all())
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
    return list(db.scalars(select(User).where(User.title.in_(assignments)).order_by(User.title, User.name)).all())


@router.post('/{user_id}/regenerate-password', response_model=UserOut)
def regenerate_password(user_id: int, db: Session = Depends(get_db), actor: User = Depends(require_system_configuration)):
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
    user.session_version += 1
    after = _snapshot(user)
    db.add(UserChangeEvent(
        event_type='USER_PASSWORD_REGENERATED', user_id=user.id, user_email=_audit_email(user.email),
        actor_user_id=actor.id, actor_email=_audit_email(actor.email),
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
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db), actor: User = Depends(require_people_write)):
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
