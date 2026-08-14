from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import current_user, require_permission
from app.core.privacy import mask_email
from app.models.entities import AccessProfile, ApprovalPolicy, ApprovalPolicyChangeEvent, User

router = APIRouter()

class PolicyInput(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    expense_type: str = 'ALL'
    min_amount: Decimal = Field(ge=0)
    max_amount: Decimal | None = Field(default=None, ge=0)
    approval_mode: str
    approver_profile_codes: list[str] = Field(min_length=1)
    active: bool = True

    @model_validator(mode='after')
    def validate_policy(self):
        if self.max_amount is not None and self.max_amount < self.min_amount:
            raise ValueError('El monto máximo no puede ser menor que el mínimo')
        if self.approval_mode not in ('ANY', 'ALL'):
            raise ValueError('Modalidad de aprobación inválida')
        return self

def output(p):
    return {'id':p.id,'name':p.name,'expense_type':p.expense_type,'min_amount':str(p.min_amount),
            'max_amount':str(p.max_amount) if p.max_amount is not None else None,
            'approval_mode':p.approval_mode,'approver_profile_codes':p.approver_profile_codes,'active':p.active}

def snapshot(p):
    return output(p)

def validate(db, data, exclude_id=None):
    valid=set(db.scalars(select(AccessProfile.code).where(AccessProfile.active.is_(True),AccessProfile.can_approve.is_(True))).all())
    if not set(data.approver_profile_codes) <= valid:
        raise HTTPException(422, 'Selecciona únicamente cargos activos con permiso para aprobar')
    if data.active:
        q=select(ApprovalPolicy).where(ApprovalPolicy.active.is_(True),
            or_(ApprovalPolicy.max_amount.is_(None),ApprovalPolicy.max_amount > data.min_amount),
            or_(data.max_amount is None, ApprovalPolicy.min_amount < data.max_amount))
        if exclude_id: q=q.where(ApprovalPolicy.id!=exclude_id)
        overlapping=db.scalars(q).first()
        if overlapping:
            other_max='sin límite' if overlapping.max_amount is None else str(overlapping.max_amount)
            raise HTTPException(409,f'El rango se superpone con la regla activa "{overlapping.name}" ({overlapping.min_amount} – {other_max})')

@router.get('/policies')
def list_policies(db:Session=Depends(get_db),_:User=Depends(current_user)):
    return [output(x) for x in db.scalars(select(ApprovalPolicy).order_by(ApprovalPolicy.expense_type,ApprovalPolicy.min_amount)).all()]

@router.post('/policies',status_code=201)
def create_policy(data:PolicyInput,db:Session=Depends(get_db),actor:User=Depends(require_permission('can_configure'))):
    validate(db,data); item=ApprovalPolicy(**data.model_dump()); db.add(item); db.flush()
    db.add(ApprovalPolicyChangeEvent(event_type='POLICY_CREATED', policy_id=item.id, policy_name=item.name,
        actor_user_id=actor.id, actor_email=mask_email(actor.email) or '***',
        changed_fields=list(data.model_dump().keys()), before_state=None, after_state=snapshot(item)))
    db.commit(); db.refresh(item); return output(item)

@router.put('/policies/{policy_id}')
def update_policy(policy_id:int,data:PolicyInput,db:Session=Depends(get_db),actor:User=Depends(require_permission('can_configure'))):
    item=db.get(ApprovalPolicy,policy_id)
    if not item: raise HTTPException(404,'Regla no encontrada')
    validate(db,data,policy_id); before=snapshot(item)
    for key,value in data.model_dump().items(): setattr(item,key,value)
    after=snapshot(item); changed=[key for key in data.model_dump() if before[key] != after[key]]
    db.add(ApprovalPolicyChangeEvent(event_type='POLICY_UPDATED', policy_id=item.id, policy_name=item.name,
        actor_user_id=actor.id, actor_email=mask_email(actor.email) or '***',
        changed_fields=changed, before_state=before, after_state=after))
    db.commit();db.refresh(item);return output(item)

@router.delete('/policies/{policy_id}',status_code=204)
def delete_policy(policy_id:int,db:Session=Depends(get_db),actor:User=Depends(require_permission('can_configure'))):
    item=db.get(ApprovalPolicy,policy_id)
    if not item: raise HTTPException(404,'Regla no encontrada')
    before=snapshot(item)
    db.add(ApprovalPolicyChangeEvent(event_type='POLICY_DELETED', policy_id=item.id, policy_name=item.name,
        actor_user_id=actor.id, actor_email=mask_email(actor.email) or '***',
        changed_fields=list(before.keys()), before_state=before, after_state=None))
    db.delete(item);db.commit()
