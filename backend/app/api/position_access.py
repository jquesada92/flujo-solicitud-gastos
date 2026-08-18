from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_permission
from app.models.iam import Position, PositionRole, Role
from app.schemas.iam import PositionOut

router = APIRouter(dependencies=[Depends(require_permission('config:manage'))])


def _position(db: Session, position_id: int) -> Position:
    position = db.get(Position, position_id)
    if not position:
        raise HTTPException(status_code=404, detail='Cargo no encontrado')
    return position


def _role(db: Session, role_id: int) -> Role:
    role = db.get(Role, role_id)
    if not role:
        raise HTTPException(status_code=404, detail='Rol no encontrado')
    if not role.active:
        raise HTTPException(status_code=422, detail='El rol está inactivo')
    if role.system_managed:
        raise HTTPException(status_code=422, detail='Un cargo no puede heredar un rol técnico administrado por el sistema')
    return role


def _out(db: Session, position: Position) -> PositionOut:
    role_ids = list(db.scalars(
        select(PositionRole.role_id)
        .where(PositionRole.position_id == position.id)
        .order_by(PositionRole.role_id)
    ).all())
    return PositionOut(
        id=position.id,
        code=position.code,
        name=position.name,
        description=position.description,
        active=position.active,
        role_ids=role_ids,
    )


@router.get('/positions', response_model=list[PositionOut])
def list_positions_with_roles(db: Session = Depends(get_db)):
    return [_out(db, item) for item in db.scalars(select(Position).order_by(Position.name)).all()]


@router.put('/positions/{position_id}/roles/{role_id}', response_model=PositionOut)
def assign_role_to_position(position_id: int, role_id: int, db: Session = Depends(get_db)):
    position = _position(db, position_id)
    role = _role(db, role_id)
    if not position.active:
        raise HTTPException(status_code=422, detail='El cargo está inactivo')
    exists = db.scalar(select(PositionRole.id).where(
        PositionRole.position_id == position.id,
        PositionRole.role_id == role.id,
    ))
    if not exists:
        db.add(PositionRole(position_id=position.id, role_id=role.id))
        db.commit()
    return _out(db, position)


@router.delete('/positions/{position_id}/roles/{role_id}', response_model=PositionOut)
def remove_role_from_position(position_id: int, role_id: int, db: Session = Depends(get_db)):
    position = _position(db, position_id)
    db.execute(delete(PositionRole).where(
        PositionRole.position_id == position.id,
        PositionRole.role_id == role_id,
    ))
    db.commit()
    return _out(db, position)
