from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.models.entities import OwnershipRole, PersonType, UserRole

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserApartmentWrite(BaseModel):
    apartment_number: str
    ownership_role: OwnershipRole

    @field_validator('apartment_number')
    @classmethod
    def valid_apartment(cls, value: str) -> str:
        value = value.strip().upper()
        if not __import__('re').fullmatch(r'(?:[6-9]|1[0-9]|2[01])[A-H]', value):
            raise ValueError('El apartamento debe estar entre 6A y 21H')
        return value


class UserApartmentOut(UserApartmentWrite):
    id: int
    class Config:
        from_attributes = True


class ApartmentResidentOut(BaseModel):
    identity_document: str
    full_name: str
    email: str
    ownership_role: OwnershipRole


class ApartmentOut(BaseModel):
    apartment_number: str
    floor: int
    letter: str
    is_rental: bool
    residents: list[ApartmentResidentOut]


class ApartmentUpdate(BaseModel):
    is_rental: bool | None = None
    owner_identity_document: str | None = None
    co_owner_identity_document: str | None = None


class UserCreate(BaseModel):
    identity_document: str = Field(min_length=5, max_length=50)
    first_name: str = Field(min_length=2, max_length=70)
    middle_name: str | None = Field(default=None, max_length=70)
    last_name: str = Field(min_length=2, max_length=70)
    second_last_name: str | None = Field(default=None, max_length=70)
    email: EmailStr
    phone: str | None = Field(default=None, min_length=7, max_length=30)
    title: str = Field(min_length=2, max_length=70)
    active: bool = True
    @field_validator('middle_name', 'second_last_name', 'phone', mode='before')
    @classmethod
    def empty_optional_fields(cls, value):
        return value if value is not None and str(value).strip() else None


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    identity_document: str | None = Field(default=None, min_length=5, max_length=50)
    first_name: str | None = Field(default=None, min_length=2, max_length=70)
    middle_name: str | None = Field(default=None, max_length=70)
    last_name: str | None = Field(default=None, min_length=2, max_length=70)
    second_last_name: str | None = Field(default=None, max_length=70)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, min_length=7, max_length=30)
    person_type: PersonType | None = None
    title: str | None = Field(default=None, min_length=2, max_length=70)
    active: bool | None = None
    apartment_number: str | None = Field(default=None, min_length=1, max_length=30)
    apartments: list[UserApartmentWrite] | None = Field(default=None, min_length=1, max_length=20)

    @field_validator('middle_name', 'second_last_name', 'phone', mode='before')
    @classmethod
    def empty_optional_fields(cls, value):
        return value if value is not None and str(value).strip() else None

    @field_validator('apartments')
    @classmethod
    def unique_updated_apartments(cls, value):
        if value is not None:
            numbers = [item.apartment_number for item in value]
            if len(numbers) != len(set(numbers)):
                raise ValueError('No puedes registrar el mismo apartamento dos veces')
        return value


class UserBulkUpdateItem(UserUpdate):
    id: int


class UserBulkUpdate(BaseModel):
    users: list[UserBulkUpdateItem] = Field(min_length=1, max_length=500)


class BoardAssignmentUpdate(BaseModel):
    president_id: int | None = None
    vice_president_id: int | None = None
    treasurer_id: int | None = None
    vocal_ids: list[int] = Field(default_factory=list, max_length=20)

    @model_validator(mode='after')
    def unique_members(self):
        ids = [item for item in (self.president_id, self.vice_president_id, self.treasurer_id) if item] + self.vocal_ids
        if len(ids) != len(set(ids)):
            raise ValueError('Una persona no puede ocupar dos cargos del mismo organigrama directivo')
        return self


class UserOut(BaseModel):
    id: int
    name: str
    full_name: str
    email: str
    identity_document: str | None
    analytics_id: str | None
    phone: str | None
    person_type: PersonType | None
    apartment_number: str | None
    first_name: str | None
    middle_name: str | None
    last_name: str | None
    second_last_name: str | None
    apartments: list[UserApartmentOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
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
