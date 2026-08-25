import logging
import threading
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.privacy import mask_email
from app.core.security import (
    apply_effective_permissions_to_user,
    create_token,
    current_user,
    decode_password_reset_token,
    hash_password,
    normalize_email,
    verify_password,
    verify_password_and_upgrade,
)
from app.models.entities import User, UserChangeEvent
from app.models.iam import SystemAccount
from app.schemas.auth import LoginResponse, TokenResponse
from app.schemas.user import ChangePasswordRequest, LoginRequest, PasswordResetRequest, PasswordResetResponse, UserOut
from app.services.email_service import send_password_reset_completed

router = APIRouter()
logger = logging.getLogger(__name__)
LOGIN_WINDOW_SECONDS = 15 * 60
LOGIN_MAX_ATTEMPTS = 5
_login_attempts: dict[str, list[float]] = {}
_login_lock = threading.Lock()
INVALID_PASSWORD_RESET_DETAIL = 'El enlace de restablecimiento no es válido o ya venció.'


def _login_key(request: Request, email: str) -> str:
    forwarded = request.headers.get('x-forwarded-for', '').split(',', 1)[0].strip()
    address = forwarded or (request.client.host if request.client else 'unknown')
    return f'{address}:{email}'


def _check_login_limit(key: str) -> None:
    now = time.monotonic()
    with _login_lock:
        recent = [stamp for stamp in _login_attempts.get(key, []) if now - stamp < LOGIN_WINDOW_SECONDS]
        if len(recent) >= LOGIN_MAX_ATTEMPTS:
            retry_after = max(1, int(LOGIN_WINDOW_SECONDS - (now - recent[0])))
            raise HTTPException(
                status_code=429,
                detail='Demasiados intentos. Intenta nuevamente más tarde',
                headers={'Retry-After': str(retry_after)},
            )
        _login_attempts[key] = recent


def _record_login_failure(key: str) -> None:
    with _login_lock:
        _login_attempts.setdefault(key, []).append(time.monotonic())


def _clear_login_failures(key: str) -> None:
    with _login_lock:
        _login_attempts.pop(key, None)


@router.post('/login', response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    email = normalize_email(str(payload.email))
    key = _login_key(request, email)
    _check_login_limit(key)
    user = db.scalar(select(User).where(func.lower(User.email) == email))
    if not user or not user.active:
        _record_login_failure(key)
        raise HTTPException(status_code=401, detail='Correo o contraseña incorrectos')

    verified, upgraded_hash = verify_password_and_upgrade(payload.password, user.password_hash)
    if not verified:
        _record_login_failure(key)
        raise HTTPException(status_code=401, detail='Correo o contraseña incorrectos')

    _clear_login_failures(key)
    if upgraded_hash:
        user.password_hash = upgraded_hash
    user.last_activity_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    apply_effective_permissions_to_user(db, user)
    return LoginResponse(access_token=create_token(user), user=UserOut.model_validate(user))


@router.get('/me', response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user


@router.post('/activity', response_model=TokenResponse)
def record_activity(db: Session = Depends(get_db), user: User = Depends(current_user)):
    user.last_activity_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return TokenResponse(access_token=create_token(user))


@router.post('/change-password', response_model=LoginResponse)
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail='La contraseña temporal no es correcta')
    if payload.current_password == payload.new_password:
        raise HTTPException(status_code=400, detail='La nueva contraseña debe ser diferente a la temporal')
    user.password_hash = hash_password(payload.new_password)
    user.must_change_password = False
    user.password_reset_version += 1
    user.session_version += 1
    user.last_activity_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    apply_effective_permissions_to_user(db, user)
    return LoginResponse(access_token=create_token(user), user=UserOut.model_validate(user))


@router.post('/reset-password', response_model=PasswordResetResponse)
def reset_password(payload: PasswordResetRequest, db: Session = Depends(get_db)):
    try:
        user_id, reset_version = decode_password_reset_token(payload.token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=INVALID_PASSWORD_RESET_DETAIL) from exc

    user = db.scalar(select(User).where(User.id == user_id).with_for_update())
    is_technical = bool(user and db.scalar(
        select(SystemAccount.id).where(SystemAccount.user_id == user.id)
    ))
    if (
        not user
        or not user.active
        or is_technical
        or user.password_reset_version != reset_version
    ):
        raise HTTPException(status_code=400, detail=INVALID_PASSWORD_RESET_DETAIL)

    previous_state = {
        'must_change_password': user.must_change_password,
        'password_reset_version': user.password_reset_version,
        'session_version': user.session_version,
    }
    user.password_hash = hash_password(payload.new_password)
    user.must_change_password = False
    user.password_reset_version += 1
    user.session_version += 1
    next_state = {
        'must_change_password': user.must_change_password,
        'password_reset_version': user.password_reset_version,
        'session_version': user.session_version,
    }
    db.add(UserChangeEvent(
        event_type='USER_PASSWORD_RESET_COMPLETED',
        user_id=user.id,
        user_email=mask_email(user.email) or '***',
        actor_user_id=user.id,
        actor_email=mask_email(user.email) or '***',
        changed_fields=['password_reset_completed', 'sessions_revoked'],
        before_state=previous_state,
        after_state=next_state,
    ))
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    try:
        send_password_reset_completed(user)
    except Exception:
        logger.warning('No se pudo enviar la confirmación de restablecimiento para user_id=%s', user.id)

    return PasswordResetResponse(message='Contraseña restablecida. Ya puedes iniciar sesión.')
