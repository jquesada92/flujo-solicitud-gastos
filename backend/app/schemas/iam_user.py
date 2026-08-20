from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class IamUserCreate(BaseModel):
    identity_document: str = Field(min_length=3, max_length=50)
    first_name: str = Field(min_length=2, max_length=70)
    middle_name: str | None = Field(default=None, max_length=70)
    last_name: str = Field(min_length=2, max_length=70)
    second_last_name: str | None = Field(default=None, max_length=70)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=30)
    active: bool = True
    group_ids: list[int] = Field(default_factory=list, max_length=100)
    role_ids: list[int] = Field(default_factory=list, max_length=100)
    # Compatibility field only. Direct user permissions are not allowed.
    direct_permission_codes: list[str] = Field(default_factory=list, max_length=100)
    # Cargo is organizational metadata; it does not grant access.
    position_ids: list[int] = Field(default_factory=list, max_length=20)

    @field_validator('middle_name', 'second_last_name', 'phone', mode='before')
    @classmethod
    def normalize_optional(cls, value):
        return value if value is not None and str(value).strip() else None

    @field_validator('direct_permission_codes')
    @classmethod
    def reject_direct_permissions(cls, value):
        if value:
            raise ValueError('Los permisos deben asignarse mediante roles; no se permiten permisos individuales')
        return []


class IamUserUpdate(BaseModel):
    identity_document: str | None = Field(default=None, min_length=3, max_length=50)
    first_name: str | None = Field(default=None, min_length=2, max_length=70)
    middle_name: str | None = Field(default=None, max_length=70)
    last_name: str | None = Field(default=None, min_length=2, max_length=70)
    second_last_name: str | None = Field(default=None, max_length=70)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    active: bool | None = None
    group_ids: list[int] | None = Field(default=None, max_length=100)
    role_ids: list[int] | None = Field(default=None, max_length=100)
    direct_permission_codes: list[str] | None = Field(default=None, max_length=100)
    position_ids: list[int] | None = Field(default=None, max_length=20)

    @field_validator('middle_name', 'second_last_name', 'phone', mode='before')
    @classmethod
    def normalize_optional(cls, value):
        return value if value is not None and str(value).strip() else None

    @field_validator('direct_permission_codes')
    @classmethod
    def reject_direct_permissions(cls, value):
        if value:
            raise ValueError('Los permisos deben asignarse mediante roles; no se permiten permisos individuales')
        return value


class IamUserOut(BaseModel):
    id: int
    name: str
    identity_document: str | None = None
    first_name: str | None = None
    middle_name: str | None = None
    last_name: str | None = None
    second_last_name: str | None = None
    email: str
    phone: str | None = None
    active: bool
    must_change_password: bool
    created_at: datetime
    updated_at: datetime
    is_system_account: bool = False
    group_ids: list[int] = Field(default_factory=list)
    role_ids: list[int] = Field(default_factory=list)
    position_ids: list[int] = Field(default_factory=list)
    # Kept in output for compatibility; authorization ignores direct permissions.
    direct_permission_codes: list[str] = Field(default_factory=list)
    effective_permission_codes: list[str] = Field(default_factory=list)
    permission_sources: dict[str, list[str]] = Field(default_factory=dict)
