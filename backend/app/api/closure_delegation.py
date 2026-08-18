from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import current_user
from app.models.entities import Expense, User
from app.schemas.closure import (
    ClosureDelegateUserOut,
    ClosureDelegationContextOut,
    ClosureDelegationCreate,
    ClosureDelegationOut,
)
from app.services.closure_service import (
    active_closure_delegation,
    assign_closure_delegate,
    can_delegate_closure,
    closure_delegation_candidates,
    is_requester,
    revoke_closure_delegate,
)
from app.services.iam_service import is_system_account

router = APIRouter()


def _expense(db: Session, request_id: str) -> Expense:
    expense = db.scalar(
        select(Expense).where(
            or_(Expense.request_id == request_id, Expense.display_id == request_id)
        )
    )
    if not expense:
        raise HTTPException(status_code=404, detail='Solicitud no encontrada')
    return expense


def _delegate_out(db: Session, expense: Expense) -> ClosureDelegationOut | None:
    delegation = active_closure_delegation(db, expense.id)
    if not delegation:
        return None
    delegate = db.get(User, delegation.delegate_user_id)
    if not delegate:
        return None
    return ClosureDelegationOut(
        id=delegation.id,
        delegate=ClosureDelegateUserOut(id=delegate.id, name=delegate.full_name, email=delegate.email),
        delegated_by_email=delegation.delegated_by_email,
        created_at=delegation.created_at,
    )


@router.get('/{request_id}/closure-delegation', response_model=ClosureDelegationContextOut)
def get_closure_delegation(
    request_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    expense = _expense(db, request_id)
    current = active_closure_delegation(db, expense.id)
    allowed_to_view = (
        is_requester(expense, user)
        or is_system_account(db, user.id)
        or (current is not None and current.delegate_user_id == user.id)
    )
    if not allowed_to_view:
        raise HTTPException(status_code=403, detail='No tienes acceso a la delegación de cierre de esta solicitud')

    can_delegate = can_delegate_closure(expense, user)
    candidates = closure_delegation_candidates(db, expense) if can_delegate else []
    return ClosureDelegationContextOut(
        can_delegate=can_delegate,
        delegation=_delegate_out(db, expense),
        candidates=[
            ClosureDelegateUserOut(id=item.id, name=item.full_name, email=item.email)
            for item in candidates
        ],
    )


@router.put('/{request_id}/closure-delegation', response_model=ClosureDelegationContextOut)
def put_closure_delegation(
    request_id: str,
    payload: ClosureDelegationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    expense = _expense(db, request_id)
    db.scalar(select(Expense.id).where(Expense.id == expense.id).with_for_update())
    if not can_delegate_closure(expense, user):
        raise HTTPException(status_code=403, detail='Solo el solicitante original puede delegar el cierre o manejo de factura')
    delegate = db.get(User, payload.delegate_user_id)
    if not delegate:
        raise HTTPException(status_code=422, detail='El usuario delegado no existe')
    try:
        assign_closure_delegate(db, expense, user, delegate)
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return ClosureDelegationContextOut(
        can_delegate=True,
        delegation=_delegate_out(db, expense),
        candidates=[
            ClosureDelegateUserOut(id=item.id, name=item.full_name, email=item.email)
            for item in closure_delegation_candidates(db, expense)
        ],
    )


@router.delete('/{request_id}/closure-delegation', response_model=ClosureDelegationContextOut)
def delete_closure_delegation(
    request_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    expense = _expense(db, request_id)
    db.scalar(select(Expense.id).where(Expense.id == expense.id).with_for_update())
    if not can_delegate_closure(expense, user):
        raise HTTPException(status_code=403, detail='Solo el solicitante original puede revocar la delegación de cierre o factura')
    try:
        revoke_closure_delegate(db, expense, user)
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return ClosureDelegationContextOut(
        can_delegate=True,
        delegation=None,
        candidates=[
            ClosureDelegateUserOut(id=item.id, name=item.full_name, email=item.email)
            for item in closure_delegation_candidates(db, expense)
        ],
    )
