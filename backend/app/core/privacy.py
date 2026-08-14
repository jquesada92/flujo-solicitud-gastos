import hashlib
import hmac
import os

from app.models.entities import PersonType, User, UserRole


def analytics_identifier(identity_document: str | None, fallback: str) -> str:
    key = os.getenv('ANALYTICS_HASH_KEY') or os.getenv('SECRET_KEY', 'development-only-change-me')
    source = (identity_document or fallback).strip().upper()
    return hmac.new(key.encode(), source.encode(), hashlib.sha256).hexdigest()


def can_view_personal_data(user: User) -> bool:
    return user.role == UserRole.ADMIN or user.person_type == PersonType.ADMINISTRATOR


def mask_email(value: str | None) -> str | None:
    if not value or '@' not in value:
        return value
    local, domain = value.split('@', 1)
    return f'{local[:1]}***@{domain}'


def mask_tail(value: str | None, visible: int = 4) -> str | None:
    if not value:
        return value
    return f'****{value[-visible:]}'
