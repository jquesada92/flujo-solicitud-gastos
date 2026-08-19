from datetime import datetime

from pydantic import BaseModel, Field


class ClosureDelegateUserOut(BaseModel):
    id: int
    name: str
    email: str


class ClosureDelegationCreate(BaseModel):
    delegate_user_id: int = Field(gt=0)


class ClosureDelegationOut(BaseModel):
    id: int
    delegate: ClosureDelegateUserOut
    delegated_by_email: str
    created_at: datetime


class ClosureDelegationContextOut(BaseModel):
    can_delegate: bool
    delegation: ClosureDelegationOut | None = None
    candidates: list[ClosureDelegateUserOut] = Field(default_factory=list)
