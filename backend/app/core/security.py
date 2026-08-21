import hashlib
import hmac
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.audit_context import set_audit_actor
from app.models.entities import User
from app.services.iam_service import effective_permission_codes, has_permission, is_system_account

bearer = HTTPBearer(auto_error=False)
password_hash = PasswordHash.recommended()

# Temporary names used by the legacy monolithic frontend/routes. They resolve to
# canonical IAM permission codes and never read the old can_* database flags.
LEGACY_PERMISSION_ALIASES = {
    'can_view': 'requests:read',
    'can_request': 'requests:create',
    'can_approve': 'requests:approve',
    'can_configure': 'config:manage',
}


def session_is_idle(last_activity_at: datetime | None, now: datetime | None = None) -> bool:
    if last_activity_at is None:
        return True
    if last_activity_at.tzinfo is None:
        last_activity_at = last_activity_at.replace(tzinfo=timezone.utc)
    current = now or datetime.now(timezone.utc)
    return current - last_activity_at >= timedelta(minutes=get_settings().session_idle_minutes)


def _verify_legacy_pbkdf2(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, expected = encoded.split('$')
        if algorithm != 'pbkdf2_sha256':
            return False
        actual = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode(),
            bytes.fromhex(salt),
            int(iterations),
        )
        return hmac.compare_digest(actual.hex(), expected)
    except (ValueError, TypeError):
        return False


def hash_password(password: str) -> str:
    """Hash new passwords with the pwdlib recommended Argon2 configuration."""
    return password_hash.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    if encoded.startswith('pbkdf2_sha256$'):
        return _verify_legacy_pbkdf2(password, encoded)
    try:
        return password_hash.verify(password, encoded)
    except Exception:
        return False


def verify_password_and_upgrade(password: str, encoded: str) -> tuple[bool, str | None]:
    """Verify a password and return a replacement Argon2 hash when needed."""
    if encoded.startswith('pbkdf2_sha256$'):
        verified = _verify_legacy_pbkdf2(password, encoded)
        return verified, hash_password(password) if verified else None
    try:
        verified, updated_hash = password_hash.verify_and_update(password, encoded)
        return verified, updated_hash
    except Exception:
        return False, None


def create_token(user: User) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            'sub': str(user.id),
            'sv': user.session_version,
            'iat': now,
            'exp': now + timedelta(minutes=settings.token_expire_minutes),
        },
        settings.secret_key,
        algorithm='HS256',
    )


def apply_effective_permissions_to_user(db: Session, user: User) -> User:
    """Attach canonical effective permissions and technical-account metadata."""
    permissions = effective_permission_codes(db, user.id)
    user.can_view = 'requests:read' in permissions
    user.can_request = 'requests:create' in permissions
    user.can_approve = 'requests:approve' in permissions
    # Compatibility output for the legacy React shell: either configuration
    # capability makes the menu visible. Runtime mutation authority continues to
    # be enforced from canonical config:manage in require_permission().
    user.can_configure = bool({'config:read', 'config:manage'} & permissions)
    user.can_close = 'requests:close' in permissions
    user.permission_codes = sorted(permissions)
    user.is_system_account = is_system_account(db, user.id)
    return user


def current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=401, detail='Debes iniciar sesión')
    try:
        payload = jwt.decode(
            credentials.credentials,
            get_settings().secret_key,
            algorithms=['HS256'],
        )
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
        raise HTTPException(
            status_code=401,
            detail=f'La sesión expiró por {get_settings().session_idle_minutes} minutos de inactividad',
        )
    if user.must_change_password and request.url.path not in (
        '/api/auth/me',
        '/api/auth/activity',
        '/api/auth/change-password',
    ):
        raise HTTPException(
            status_code=403,
            detail='Debes cambiar tu contraseña temporal antes de continuar',
        )

    set_audit_actor(
        db,
        user_id=user.id,
        identifier=user.email,
        identity_document=user.identity_document,
    )
    return apply_effective_permissions_to_user(db, user)


def require_permission(permission_code: str):
    """Authorize solely from effective permissions persisted in PostgreSQL.

    config:read is intentionally a read-only companion to config:manage. It may
    satisfy a legacy config:manage guard only for safe HTTP reads; every mutation
    still requires config:manage regardless of what the frontend renders.
    """
    canonical_code = LEGACY_PERMISSION_ALIASES.get(permission_code, permission_code)

    def dependency(
        request: Request,
        user: User = Depends(current_user),
        db: Session = Depends(get_db),
    ) -> User:
        if (
            canonical_code == 'config:manage'
            and request.method in {'GET', 'HEAD'}
            and has_permission(db, user.id, 'config:read')
        ):
            return user
        if not has_permission(db, user.id, canonical_code):
            raise HTTPException(status_code=403, detail='No tienes permiso para realizar esta acción')
        return user

    return dependency


def require_system_account(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> User:
    """Protect technical administration independently of mutable IAM assignments."""
    if not is_system_account(db, user.id):
        raise HTTPException(status_code=403, detail='Esta función está reservada al Administrador del sistema')
    return user


def normalize_email(email: str) -> str:
    return email.strip().lower()
