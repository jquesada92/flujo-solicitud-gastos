import re
import unicodedata
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.security import current_user, require_permission
from app.models.entities import ExpenseArea, ExpenseSubcategory, User
from app.schemas.area import AreaCreate, AreaOut, AreaUpdate, SubcategoryCreate, SubcategoryOut

router = APIRouter()


def _base_code(name: str) -> str:
    normalized = unicodedata.normalize('NFKD', name)
    ascii_name = ''.join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r'[^A-Z]+', '_', ascii_name.upper()).strip('_')[:70]


def _unique_area_code(db: Session, name: str) -> str:
    base = _base_code(name)
    code, sequence = base, 2
    while db.scalar(select(ExpenseArea.id).where(ExpenseArea.code == code)):
        code = f'{base}_{sequence}'
        sequence += 1
    return code


def _unique_subcategory_code(db: Session, area_id: int, name: str) -> str:
    base = _base_code(name)
    code, sequence = base, 2
    while db.scalar(select(ExpenseSubcategory.id).where(
        ExpenseSubcategory.area_id == area_id,
        ExpenseSubcategory.code == code,
    )):
        code = f'{base}_{sequence}'
        sequence += 1
    return code


def _area(db: Session, area_id: int) -> ExpenseArea:
    item = db.scalar(
        select(ExpenseArea)
        .where(ExpenseArea.id == area_id)
        .options(selectinload(ExpenseArea.subcategories))
    )
    if not item:
        raise HTTPException(status_code=404, detail='Área no encontrada')
    return item


@router.get('', response_model=list[AreaOut])
def list_areas(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    stmt = select(ExpenseArea).options(selectinload(ExpenseArea.subcategories)).order_by(ExpenseArea.name)
    if not include_inactive or not (user.role.value == 'ADMIN' or user.can_configure):
        stmt = stmt.where(ExpenseArea.active.is_(True))
    items = list(db.scalars(stmt).all())
    if not include_inactive:
        for item in items:
            item.subcategories = [sub for sub in item.subcategories if sub.active]
    return items


@router.post('', response_model=AreaOut, status_code=201, dependencies=[Depends(require_permission('can_configure'))])
def create_area(payload: AreaCreate, db: Session = Depends(get_db)):
    item = ExpenseArea(code=_unique_area_code(db, payload.name), name=payload.name)
    db.add(item)
    db.commit()
    db.refresh(item)
    return _area(db, item.id)


@router.patch('/{area_id}', response_model=AreaOut, dependencies=[Depends(require_permission('can_configure'))])
def update_area(area_id: int, payload: AreaUpdate, db: Session = Depends(get_db)):
    item = _area(db, area_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value.strip() if key == 'name' else value)
    db.commit()
    return _area(db, area_id)


@router.post('/{area_id}/subcategories', response_model=SubcategoryOut, status_code=201, dependencies=[Depends(require_permission('can_configure'))])
def create_subcategory(area_id: int, payload: SubcategoryCreate, db: Session = Depends(get_db)):
    _area(db, area_id)
    item = ExpenseSubcategory(area_id=area_id, code=_unique_subcategory_code(db, area_id, payload.name), name=payload.name)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch('/subcategories/{subcategory_id}', response_model=SubcategoryOut, dependencies=[Depends(require_permission('can_configure'))])
def update_subcategory(subcategory_id: int, payload: AreaUpdate, db: Session = Depends(get_db)):
    item = db.get(ExpenseSubcategory, subcategory_id)
    if not item:
        raise HTTPException(status_code=404, detail='Subcategoría no encontrada')
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value.strip() if key == 'name' else value)
    db.commit()
    db.refresh(item)
    return item
