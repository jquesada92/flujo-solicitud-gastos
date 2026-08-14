import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.entities import User, UserRole

bearer = HTTPBearer(auto_error=False)
SECRET_KEY = os.getenv('SECRET_KEY', 'development-only-change-me')
TOKEN_MINUTES = int(os.getenv('TOKEN_EXPIRE_MINUTES', '480'))
SESSION_IDLE_MINUTES = int(os.getenv('SESSION_IDLE_MINUTES', '30'))


def session_is_idle(last_activity_at: datetime | None, now: datetime | None = None) -> bool:
    if last_activity_at is None:
        return True
    if last_activity_at.tzinfo is None:
        last_activity_at = last_activity_at.replace(tzinfo=timezone.utc)
    current = now or datetime.now(timezone.utc)
    return current - last_activity_at >= timedelta(minutes=SESSION_IDLE_MINUTES)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 600_000)
    return f'pbkdf2_sha256$600000${salt.hex()}${digest.hex()}'


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, expected = encoded.split('$')
        if algorithm != 'pbkdf2_sha256':
            return False
        actual = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), int(iterations))
        return hmac.compare_digest(actual.hex(), expected)
    except (ValueError, TypeError):
        return False


def create_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({
        'sub': str(user.id),
        'sv': user.session_version,
        'iat': now,
        'exp': now + timedelta(minutes=TOKEN_MINUTES),
    }, SECRET_KEY, algorithm='HS256')


def current_user(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if not credentials:
        raise HTTPException(status_code=401, detail='Debes iniciar sesión')
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=['HS256'])
        user_id = int(payload['sub'])
        session_version = int(payload['sv'])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail='Sesión inválida o vencida')
    user = db.get(User, user_id)
    if not user or not user.active:
        raise HTTPException(status_code=401, detail='Usuario inactivo o inexistente')
    if user.session_version != session_version:
        raise HTTPException(status_code=401, detail='La sesión fue revocada. Inicia sesión nuevamente')
    if session_is_idle(user.last_activity_at):
        raise HTTPException(status_code=401, detail=f'La sesión expiró por {SESSION_IDLE_MINUTES} minutos de inactividad')
    if user.must_change_password and request.url.path not in ('/api/auth/me', '/api/auth/activity', '/api/auth/change-password'):
        raise HTTPException(status_code=403, detail='Debes cambiar tu contraseña temporal antes de continuar')
    return user


def require_roles(*roles: UserRole):
    def dependency(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail='No tienes permiso para realizar esta acción')
        return user
    return dependency


def require_permission(permission: str):
    def dependency(user: User = Depends(current_user)) -> User:
        if user.role != UserRole.ADMIN and not getattr(user, permission, False):
            raise HTTPException(status_code=403, detail='No tienes permiso para realizar esta acción')
        return user
    return dependency


def normalize_email(email: str) -> str:
    return email.strip().lower()
