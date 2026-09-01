from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, StrictInt, model_validator
from sqlalchemy import or_, select, text
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import require_permission
from app.models.entities import ApprovalPolicy, ExpenseArea, User
from app.services.approval_policy_service import (
    APPROVAL_MODES,
    NO_APPROVAL_MODE,
    eligible_approver_group_ids,
    eligible_approver_role_ids,
    eligible_approver_targets,
)

router = APIRouter()

class PolicyInput(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    expense_type: str = 'ALL'
    min_amount: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    max_amount: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=12,
        decimal_places=2,
    )
    approval_mode: str
    approver_profile_codes: list[str] = Field(default_factory=list)
    approver_role_ids: list[StrictInt] = Field(default_factory=list)
    approver_group_ids: list[StrictInt] = Field(default_factory=list)
    active: bool = True

    @model_validator(mode='after')
    def validate_policy(self):
        if self.max_amount is not None and self.max_amount <= self.min_amount:
            raise ValueError('El monto máximo debe ser mayor que el mínimo')
        if self.approval_mode not in APPROVAL_MODES:
            raise ValueError('Modalidad de aprobación inválida')
        if any(isinstance(value, bool) or value < 1 for value in self.approver_role_ids):
            raise ValueError('Los identificadores de Rol deben ser enteros positivos')
        if any(isinstance(value, bool) or value < 1 for value in self.approver_group_ids):
            raise ValueError('Los identificadores de Grupo deben ser enteros positivos')
        self.approver_role_ids = list(dict.fromkeys(self.approver_role_ids))
        self.approver_group_ids = list(dict.fromkeys(self.approver_group_ids))
        has_targets = bool(self.approver_role_ids or self.approver_group_ids)
        if self.approval_mode == NO_APPROVAL_MODE and has_targets:
            raise ValueError('Una regla sin aprobación no admite Roles ni Grupos aprobadores')
        if self.approval_mode != NO_APPROVAL_MODE and not has_targets:
            raise ValueError('Selecciona al menos un Rol o Grupo aprobador')
        return self

def output(p):
    return {'id':p.id,'name':p.name,'expense_type':p.expense_type,'min_amount':str(p.min_amount),
            'max_amount':str(p.max_amount) if p.max_amount is not None else None,
            'approval_mode':p.approval_mode,'approver_profile_codes':p.approver_profile_codes,
            'approver_role_ids':p.approver_role_ids or [],'approver_group_ids':p.approver_group_ids or [],
            'active':p.active}

def validate(db, data, exclude_id=None):
    if data.expense_type != 'ALL':
        area_exists = db.scalar(select(ExpenseArea.id).where(
            ExpenseArea.code == data.expense_type,
            ExpenseArea.active.is_(True),
        ))
        if not area_exists:
            raise HTTPException(422, 'El área de la regla no existe o está inactiva')

    role_ids = set(data.approver_role_ids)
    group_ids = set(data.approver_group_ids)
    invalid_roles = role_ids - eligible_approver_role_ids(db)
    invalid_groups = group_ids - eligible_approver_group_ids(db)
    if invalid_roles or invalid_groups:
        raise HTTPException(
            422,
            'Selecciona únicamente Roles o Grupos activos con permiso efectivo requests:approve',
        )

    # PostgreSQL needs a scope lock in addition to row locks: two concurrent
    # inserts into an empty Area otherwise cannot see one another. SQLite tests
    # serialize writes and do not expose pg_advisory_xact_lock.
    if db.get_bind().dialect.name == 'postgresql':
        db.execute(
            text('SELECT pg_advisory_xact_lock(hashtext(:scope))'),
            {'scope': f'approval-policy:{data.expense_type}'},
        )
    if data.active:
        q=select(ApprovalPolicy).where(ApprovalPolicy.active.is_(True),
            ApprovalPolicy.expense_type == data.expense_type,
            or_(ApprovalPolicy.max_amount.is_(None),ApprovalPolicy.max_amount > data.min_amount),
            or_(data.max_amount is None, ApprovalPolicy.min_amount < data.max_amount)).with_for_update()
        if exclude_id: q=q.where(ApprovalPolicy.id!=exclude_id)
        overlapping=db.scalars(q).first()
        if overlapping:
            other_max='sin límite' if overlapping.max_amount is None else str(overlapping.max_amount)
            raise HTTPException(409,f'El rango se superpone con la regla activa "{overlapping.name}" ({overlapping.min_amount} – {other_max})')

@router.get('/policies')
def list_policies(db:Session=Depends(get_db),_:User=Depends(require_permission('can_configure'))):
    return [output(x) for x in db.scalars(select(ApprovalPolicy).order_by(ApprovalPolicy.expense_type,ApprovalPolicy.min_amount)).all()]


@router.get('/approver-targets')
def list_approver_targets(db:Session=Depends(get_db),_:User=Depends(require_permission('can_configure'))):
    roles, groups = eligible_approver_targets(db)
    return {
        'roles': [
            {
                'id': item.id,
                'name': item.name,
                'group_id': item.group_id,
                'group_name': item.group_name,
            }
            for item in roles
        ],
        'groups': [
            {'id': item.id, 'name': item.name, 'role_count': item.role_count}
            for item in groups
        ],
    }

@router.post('/policies',status_code=201)
def create_policy(data:PolicyInput,db:Session=Depends(get_db),actor:User=Depends(require_permission('can_configure'))):
    validate(db,data); item=ApprovalPolicy(**data.model_dump()); db.add(item); db.flush()
    db.commit(); db.refresh(item); return output(item)

@router.put('/policies/{policy_id}')
def update_policy(policy_id:int,data:PolicyInput,db:Session=Depends(get_db),actor:User=Depends(require_permission('can_configure'))):
    item=db.get(ApprovalPolicy,policy_id)
    if not item: raise HTTPException(404,'Regla no encontrada')
    validate(db,data,policy_id)
    for key,value in data.model_dump().items(): setattr(item,key,value)
    db.commit();db.refresh(item);return output(item)

@router.delete('/policies/{policy_id}',status_code=204)
def delete_policy(policy_id:int,db:Session=Depends(get_db),actor:User=Depends(require_permission('can_configure'))):
    item=db.get(ApprovalPolicy,policy_id)
    if not item: raise HTTPException(404,'Regla no encontrada')
    db.delete(item);db.commit()
