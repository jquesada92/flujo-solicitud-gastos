from functools import lru_cache
from pathlib import Path
import re

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_DATABASE_SCHEMA_PATTERN = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
_RESERVED_DATABASE_SCHEMAS = {'public', 'pg_catalog', 'information_schema'}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
        case_sensitive=False,
    )

    environment: str = 'development'
    render: bool = False
    database_url: str
    database_schema: str = 'administracion'

    secret_key: str = 'development-only-change-me'
    analytics_hash_key: str = ''
    token_expire_minutes: int = Field(default=480, ge=5, le=10080)
    password_reset_token_expire_minutes: int = Field(default=30, ge=5, le=1440)
    session_idle_minutes: int = Field(default=30, ge=5, le=1440)

    public_url: str = 'http://localhost:5173'
    cors_allowed_origins: str = 'http://localhost:3000,http://localhost:5173'
    app_time_zone: str = 'America/Panama'

    user_read_rate_limit: int = Field(default=120, ge=1)
    user_write_rate_limit: int = Field(default=30, ge=1)
    user_upload_rate_limit: int = Field(default=6, ge=1)
    user_sensitive_rate_limit: int = Field(default=10, ge=1)

    upload_dir: Path = Path('/app/uploads')
    max_upload_storage_mb: int = Field(default=450, ge=1)

    email_mode: str = 'console'
    email_from: str = 'noreply@example.com'
    brevo_api_key: str | None = None
    brevo_sender_name: str = 'Gestión de Gastos'
    smtp_host: str = 'smtp.gmail.com'
    smtp_port: int = Field(default=465, ge=1, le=65535)
    smtp_user: str = ''
    smtp_password: str = ''
    smtp_security: str = 'ssl'

    admin_name: str = 'Administrador del sistema'
    admin_email: str = 'admin@example.com'
    admin_password: str = 'Admin123!'

    @property
    def is_production_environment(self) -> bool:
        """True only when business authorization must use production policy."""
        return self.environment.strip().lower() == 'production'

    @property
    def is_production(self) -> bool:
        """Security-hardening flag retained for hosted runtime validation.

        Render preview/dev services still require strong secrets and explicit
        CORS, but they do not inherit production-only segregation-of-duties
        behavior unless ENVIRONMENT=production.
        """
        return self.is_production_environment or self.render

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip().rstrip('/')
            for origin in self.cors_allowed_origins.split(',')
            if origin.strip()
        ]

    @field_validator('database_schema')
    @classmethod
    def validate_database_schema(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized or not _DATABASE_SCHEMA_PATTERN.fullmatch(normalized):
            raise ValueError(
                'DATABASE_SCHEMA debe ser un identificador PostgreSQL simple '
                '(letras, números y guion bajo; no puede iniciar con número)'
            )
        lowered = normalized.lower()
        if lowered in _RESERVED_DATABASE_SCHEMAS or lowered.startswith('pg_'):
            raise ValueError('DATABASE_SCHEMA debe ser un schema dedicado de la aplicación, no un schema del sistema')
        return normalized

    @field_validator('email_mode')
    @classmethod
    def validate_email_mode(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {'console', 'brevo', 'smtp'}:
            raise ValueError('EMAIL_MODE debe ser console, brevo o smtp')
        return normalized

    @field_validator('smtp_security')
    @classmethod
    def validate_smtp_security(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {'ssl', 'starttls'}:
            raise ValueError('SMTP_SECURITY debe ser ssl o starttls')
        return normalized

    @model_validator(mode='after')
    def validate_runtime_configuration(self):
        errors: list[str] = []
        if self.email_mode == 'smtp' and (not self.smtp_user or not self.smtp_password):
            errors.append('SMTP_USER y SMTP_PASSWORD son obligatorios cuando EMAIL_MODE=smtp')
        if self.email_mode == 'brevo' and not self.brevo_api_key:
            errors.append('BREVO_API_KEY es obligatorio cuando EMAIL_MODE=brevo')

        if self.is_production:
            if len(self.secret_key) < 32 or self.secret_key == 'development-only-change-me':
                errors.append('SECRET_KEY debe contener al menos 32 caracteres')
            if len(self.analytics_hash_key) < 32 or self.analytics_hash_key == self.secret_key:
                errors.append('ANALYTICS_HASH_KEY debe ser distinto de SECRET_KEY y tener al menos 32 caracteres')
            if len(self.admin_password) < 12 or self.admin_password == 'Admin123!':
                errors.append('ADMIN_PASSWORD debe contener al menos 12 caracteres')
            if not self.cors_origins or '*' in self.cors_origins or any(
                not origin.startswith('https://') for origin in self.cors_origins
            ):
                errors.append('CORS_ALLOWED_ORIGINS debe contener únicamente orígenes HTTPS explícitos')

        if errors:
            raise ValueError('; '.join(errors))
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
