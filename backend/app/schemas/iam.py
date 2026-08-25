from pydantic import BaseModel, Field


class PermissionOut(BaseModel):
    id: int
    code: str
    name: str
    description: str | None = None
    active: bool

    class Config:
        from_attributes = True


class RoleWrite(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=1000)
    permission_codes: list[str] = Field(default_factory=list, max_length=100)
    active: bool = True
    max_users: int | None = Field(default=None, ge=1)


class RoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=1000)
    permission_codes: list[str] | None = Field(default=None, max_length=100)
    active: bool | None = None
    max_users: int | None = Field(default=None, ge=1)


class RoleOut(BaseModel):
    id: int
    code: str
    name: str
    description: str | None = None
    active: bool
    system_managed: bool
    max_users: int | None = None
    assigned_user_count: int = 0
    permission_codes: list[str] = Field(default_factory=list)


class GroupWrite(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=1000)
    permission_codes: list[str] = Field(default_factory=list, max_length=100)
    active: bool = True


class GroupUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=1000)
    permission_codes: list[str] | None = Field(default=None, max_length=100)
    active: bool | None = None


class GroupOut(BaseModel):
    id: int
    code: str
    name: str
    description: str | None = None
    active: bool
    permission_codes: list[str] = Field(default_factory=list)
    role_ids: list[int] = Field(default_factory=list)
    member_ids: list[int] = Field(default_factory=list)


class PositionWrite(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=1000)
    active: bool = True


class PositionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=1000)
    active: bool | None = None


class PositionOut(BaseModel):
    id: int
    code: str
    name: str
    description: str | None = None
    active: bool
    role_ids: list[int] = Field(default_factory=list)


class EffectiveAccessOut(BaseModel):
    user_id: int
    permission_codes: list[str]
    sources: dict[str, list[str]]
