from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, model_validator

from app.models.entities import UserRole

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    title: str = Field(min_length=2, max_length=70)


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    title: str | None = Field(default=None, min_length=2, max_length=70)
    active: bool | None = None


class UserBulkUpdateItem(UserUpdate):
    id: int


class UserBulkUpdate(BaseModel):
    users: list[UserBulkUpdateItem] = Field(min_length=1, max_length=500)


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: UserRole
    title: str
    active: bool
    can_request: bool
    can_approve: bool
    can_view: bool
    can_configure: bool
    must_change_password: bool

    class Config:
        from_attributes = True


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=10, max_length=128)


class UserChangeEventOut(BaseModel):
    event_sequence: int
    event_id: str
    occurred_at: datetime
    event_type: str
    user_id: int
    user_email: str
    actor_email: str
    changed_fields: list[str]
    before_state: dict | None
    after_state: dict

    class Config:
        from_attributes = True


class AccessProfileWrite(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    can_request: bool = False
    can_approve: bool = False
    can_view: bool = True
    can_configure: bool = False
    has_user_limit: bool = False
    max_users: int | None = Field(default=None, ge=1, le=10000)
    active: bool = True

    @model_validator(mode='after')
    def validate_limit(self):
        if self.has_user_limit and self.max_users is None:
            raise ValueError('Debes indicar el número máximo de personas')
        if not self.has_user_limit:
            self.max_users = None
        return self


class AccessProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    can_request: bool | None = None
    can_approve: bool | None = None
    can_view: bool | None = None
    can_configure: bool | None = None
    has_user_limit: bool | None = None
    max_users: int | None = Field(default=None, ge=1, le=10000)
    active: bool | None = None


class AccessProfileOut(AccessProfileWrite):
    id: int
    code: str

    class Config:
        from_attributes = True
