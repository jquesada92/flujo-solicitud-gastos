import threading
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_token, current_user, hash_password, normalize_email, verify_password
from app.models.entities import User
from app.schemas.user import ChangePasswordRequest, LoginRequest, UserOut

router = APIRouter()
LOGIN_WINDOW_SECONDS = 15 * 60
LOGIN_MAX_ATTEMPTS = 5
_login_attempts: dict[str, list[float]] = {}
_login_lock = threading.Lock()


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


@router.post('/login')
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    email = normalize_email(str(payload.email))
    key = _login_key(request, email)
    _check_login_limit(key)
    user = db.scalar(select(User).where(func.lower(User.email) == email))
    if not user or not user.active or not verify_password(payload.password, user.password_hash):
        _record_login_failure(key)
        raise HTTPException(status_code=401, detail='Correo o contraseña incorrectos')
    _clear_login_failures(key)
    user.last_activity_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return {'access_token': create_token(user), 'token_type': 'bearer', 'user': UserOut.model_validate(user)}


@router.get('/me', response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user


@router.post('/activity')
def record_activity(db: Session = Depends(get_db), user: User = Depends(current_user)):
    user.last_activity_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return {'access_token': create_token(user), 'token_type': 'bearer'}


@router.post('/change-password')
def change_password(payload: ChangePasswordRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail='La contraseña temporal no es correcta')
    if payload.current_password == payload.new_password:
        raise HTTPException(status_code=400, detail='La nueva contraseña debe ser diferente a la temporal')
    user.password_hash = hash_password(payload.new_password)
    user.must_change_password = False
    user.session_version += 1
    user.last_activity_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return {'access_token': create_token(user), 'token_type': 'bearer', 'user': UserOut.model_validate(user)}
