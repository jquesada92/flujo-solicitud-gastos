import os
import re
import unicodedata
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload
from app.core.database import get_db
from app.core.security import current_user, normalize_email, require_permission
from app.models.entities import ApprovalRule, ExpenseCategory, ExpenseSubcategory, User
from app.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate, SubcategoryCreate, SubcategoryOut

router = APIRouter()


def _base_code(name: str) -> str:
    normalized = unicodedata.normalize('NFKD', name)
    ascii_name = ''.join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r'[^A-Z]+', '_', ascii_name.upper()).strip('_')[:70]


def _unique_category_code(db: Session, name: str) -> str:
    base = _base_code(name)
    code, sequence = base, 2
    while db.scalar(select(ExpenseCategory.id).where(ExpenseCategory.code == code)):
        code=f'{base}_{sequence}'; sequence += 1
    return code


def _unique_subcategory_code(db: Session, category_id: int, name: str) -> str:
    base = _base_code(name)
    code, sequence = base, 2
    while db.scalar(select(ExpenseSubcategory.id).where(ExpenseSubcategory.category_id == category_id, ExpenseSubcategory.code == code)):
        code=f'{base}_{sequence}'; sequence += 1
    return code


def _category(db: Session, category_id: int) -> ExpenseCategory:
    item = db.scalar(select(ExpenseCategory).where(ExpenseCategory.id == category_id).options(selectinload(ExpenseCategory.subcategories)))
    if not item:
        raise HTTPException(status_code=404, detail='Categoría no encontrada')
    return item


@router.get('', response_model=list[CategoryOut])
def list_categories(include_inactive: bool = False, db: Session = Depends(get_db), user: User = Depends(current_user)):
    stmt = select(ExpenseCategory).options(selectinload(ExpenseCategory.subcategories)).order_by(ExpenseCategory.name)
    if not include_inactive or not (user.role.value == 'ADMIN' or user.can_configure):
        stmt = stmt.where(ExpenseCategory.active.is_(True))
    items = list(db.scalars(stmt).all())
    if not include_inactive:
        for item in items:
            item.subcategories = [sub for sub in item.subcategories if sub.active]
    return items


@router.post('', response_model=CategoryOut, status_code=201, dependencies=[Depends(require_permission('can_configure'))])
def create_category(payload: CategoryCreate, db: Session = Depends(get_db)):
    item = ExpenseCategory(code=_unique_category_code(db, payload.name), name=payload.name)
    db.add(item)
    treasurer = normalize_email(os.getenv('TREASURER_EMAIL', 'tesorero@example.com'))
    president = normalize_email(os.getenv('PRESIDENT_EMAIL', 'presidente@example.com'))
    db.add_all([
        ApprovalRule(expense_type=item.code, min_amount=Decimal('0'), max_amount=None, approver_email=treasurer, approver_role='TESORERO', step=1),
        ApprovalRule(expense_type=item.code, min_amount=Decimal('0'), max_amount=None, approver_email=president, approver_role='PRESIDENTE', step=2),
    ])
    db.commit(); db.refresh(item)
    return _category(db, item.id)


@router.patch('/{category_id}', response_model=CategoryOut, dependencies=[Depends(require_permission('can_configure'))])
def update_category(category_id: int, payload: CategoryUpdate, db: Session = Depends(get_db)):
    item = _category(db, category_id)
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(item, key, value.strip() if key == 'name' else value)
    db.commit(); return _category(db, category_id)


@router.post('/{category_id}/subcategories', response_model=SubcategoryOut, status_code=201, dependencies=[Depends(require_permission('can_configure'))])
def create_subcategory(category_id: int, payload: SubcategoryCreate, db: Session = Depends(get_db)):
    _category(db, category_id)
    item = ExpenseSubcategory(category_id=category_id, code=_unique_subcategory_code(db, category_id, payload.name), name=payload.name)
    db.add(item); db.commit(); db.refresh(item); return item


@router.patch('/subcategories/{subcategory_id}', response_model=SubcategoryOut, dependencies=[Depends(require_permission('can_configure'))])
def update_subcategory(subcategory_id: int, payload: CategoryUpdate, db: Session = Depends(get_db)):
    item = db.get(ExpenseSubcategory, subcategory_id)
    if not item: raise HTTPException(status_code=404, detail='Subcategoría no encontrada')
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(item, key, value.strip() if key == 'name' else value)
    db.commit(); db.refresh(item); return item
