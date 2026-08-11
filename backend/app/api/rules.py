from decimal import Decimal
from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import current_user, normalize_email, require_roles
from app.models.entities import ApprovalRule, User, UserRole

router = APIRouter()


class RuleCreate(BaseModel):
    expense_type: str
    min_amount: Decimal = Field(ge=0)
    max_amount: Decimal | None = Field(default=None, gt=0)
    approver_email: EmailStr
    approver_role: str
    step: int = Field(ge=1)


@router.get('')
def list_rules(db: Session = Depends(get_db), _: User = Depends(current_user)):
    rules = db.scalars(select(ApprovalRule).order_by(ApprovalRule.expense_type, ApprovalRule.min_amount, ApprovalRule.step)).all()
    return [
        {
            'id': r.id,
            'expense_type': r.expense_type,
            'min_amount': str(r.min_amount),
            'max_amount': str(r.max_amount) if r.max_amount is not None else None,
            'approver_email': r.approver_email,
            'approver_role': r.approver_role,
            'step': r.step,
            'active': r.active,
        }
        for r in rules
    ]


@router.post('', status_code=201)
def create_rule(payload: RuleCreate, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.ADMIN))):
    values = payload.model_dump()
    values['approver_email'] = normalize_email(str(values['approver_email']))
    rule = ApprovalRule(**values)
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return {'id': rule.id}
