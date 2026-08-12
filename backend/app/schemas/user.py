from pydantic import BaseModel, EmailStr, Field

from app.models.entities import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: UserRole
    can_request: bool | None = None
    can_approve: bool | None = None
    can_view: bool | None = None
    can_configure: bool | None = None


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    role: UserRole | None = None
    active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
    can_request: bool | None = None
    can_approve: bool | None = None
    can_view: bool | None = None
    can_configure: bool | None = None


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: UserRole
    active: bool
    can_request: bool
    can_approve: bool
    can_view: bool
    can_configure: bool

    class Config:
        from_attributes = True
