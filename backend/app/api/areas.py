import re
import unicodedata

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import current_user, require_permission
from app.models.classification import AreaCategoryLink, ExpenseCategoryCatalog
from app.models.entities import ExpenseArea, ExpenseSubcategory, User
from app.schemas.area import AreaCreate, AreaOut, AreaUpdate, CategoryCreate, CategoryOut, CategoryUpdate
from app.services.iam_service import has_permission

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


def _unique_category_code(db: Session, name: str) -> str:
    base = _base_code(name)
    code, sequence = base, 2
    while db.scalar(select(ExpenseCategoryCatalog.id).where(ExpenseCategoryCatalog.code == code)):
        code = f'{base}_{sequence}'
        sequence += 1
    return code


def _ensure_category_catalog(db: Session) -> None:
    legacy_rows = list(db.scalars(select(ExpenseSubcategory)).all())
    if not legacy_rows:
        return
    changed = False
    categories_by_code = {item.code: item for item in db.scalars(select(ExpenseCategoryCatalog)).all()}
    for legacy in legacy_rows:
        category = categories_by_code.get(legacy.code)
        if not category:
            category = ExpenseCategoryCatalog(code=legacy.code, name=legacy.name, active=legacy.active)
            db.add(category)
            db.flush()
            categories_by_code[legacy.code] = category
            changed = True
        elif legacy.active and not category.active:
            category.active = True
            changed = True
        link = db.scalar(select(AreaCategoryLink.id).where(
            AreaCategoryLink.area_id == legacy.area_id,
            AreaCategoryLink.category_id == category.id,
        ))
        if not link:
            db.add(AreaCategoryLink(area_id=legacy.area_id, category_id=category.id))
            changed = True
    if changed:
        db.commit()


def _area(db: Session, area_id: int) -> ExpenseArea:
    item = db.get(ExpenseArea, area_id)
    if not item:
        raise HTTPException(status_code=404, detail='Área no encontrada')
    return item


def _category(db: Session, category_id: int) -> ExpenseCategoryCatalog:
    _ensure_category_catalog(db)
    item = db.get(ExpenseCategoryCatalog, category_id)
    if not item:
        raise HTTPException(status_code=404, detail='Categoría no encontrada')
    return item


def _category_out(db: Session, category: ExpenseCategoryCatalog) -> dict:
    area_ids = list(db.scalars(select(AreaCategoryLink.area_id).where(
        AreaCategoryLink.category_id == category.id,
    ).order_by(AreaCategoryLink.area_id)).all())
    return {
        'id': category.id,
        'code': category.code,
        'name': category.name,
        'active': category.active,
        'area_ids': area_ids,
    }


def _area_out(db: Session, area: ExpenseArea, include_inactive: bool = False) -> dict:
    stmt = (
        select(ExpenseCategoryCatalog)
        .join(AreaCategoryLink, AreaCategoryLink.category_id == ExpenseCategoryCatalog.id)
        .where(AreaCategoryLink.area_id == area.id)
        .order_by(ExpenseCategoryCatalog.name)
    )
    if not include_inactive:
        stmt = stmt.where(ExpenseCategoryCatalog.active.is_(True))
    categories = list(db.scalars(stmt).all())
    return {
        'id': area.id,
        'code': area.code,
        'name': area.name,
        'active': area.active,
        'categories': [_category_out(db, item) for item in categories],
    }


def _link_category(db: Session, area: ExpenseArea, category: ExpenseCategoryCatalog) -> None:
    existing_link = db.scalar(select(AreaCategoryLink.id).where(
        AreaCategoryLink.area_id == area.id,
        AreaCategoryLink.category_id == category.id,
    ))
    if existing_link:
        raise HTTPException(status_code=409, detail='La categoría ya está habilitada para esta área')
    db.add(AreaCategoryLink(area_id=area.id, category_id=category.id))
    legacy = db.scalar(select(ExpenseSubcategory).where(
        ExpenseSubcategory.area_id == area.id,
        ExpenseSubcategory.code == category.code,
    ))
    if legacy:
        legacy.name = category.name
        legacy.active = category.active
    else:
        db.add(ExpenseSubcategory(
            area_id=area.id,
            code=category.code,
            name=category.name,
            active=category.active,
        ))


@router.get('', response_model=list[AreaOut])
def list_areas(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    _ensure_category_catalog(db)
    include_all = include_inactive and has_permission(db, user.id, 'areas:manage')
    stmt = select(ExpenseArea).order_by(ExpenseArea.name)
    if not include_all:
        stmt = stmt.where(ExpenseArea.active.is_(True))
    return [_area_out(db, item, include_all) for item in db.scalars(stmt).all()]


@router.post('', response_model=AreaOut, status_code=201, dependencies=[Depends(require_permission('areas:manage'))])
def create_area(payload: AreaCreate, db: Session = Depends(get_db)):
    item = ExpenseArea(code=_unique_area_code(db, payload.name), name=payload.name)
    db.add(item)
    db.commit()
    db.refresh(item)
    return _area_out(db, item)


@router.patch('/{area_id}', response_model=AreaOut, dependencies=[Depends(require_permission('areas:manage'))])
def update_area(area_id: int, payload: AreaUpdate, db: Session = Depends(get_db)):
    item = _area(db, area_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value.strip() if key == 'name' else value)
    db.commit()
    db.refresh(item)
    return _area_out(db, item, include_inactive=True)


@router.get('/categories', response_model=list[CategoryOut])
def list_categories(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    _ensure_category_catalog(db)
    include_all = include_inactive and has_permission(db, user.id, 'areas:manage')
    stmt = select(ExpenseCategoryCatalog).order_by(ExpenseCategoryCatalog.name)
    if not include_all:
        stmt = stmt.where(ExpenseCategoryCatalog.active.is_(True))
    return [_category_out(db, item) for item in db.scalars(stmt).all()]


@router.post('/categories', response_model=CategoryOut, status_code=201, dependencies=[Depends(require_permission('areas:manage'))])
def create_category(payload: CategoryCreate, db: Session = Depends(get_db)):
    _ensure_category_catalog(db)
    duplicate = db.scalar(select(ExpenseCategoryCatalog).where(
        func.lower(ExpenseCategoryCatalog.name) == payload.name.lower()
    ))
    if duplicate:
        raise HTTPException(status_code=409, detail='Ya existe una categoría con ese nombre')
    item = ExpenseCategoryCatalog(code=_unique_category_code(db, payload.name), name=payload.name)
    db.add(item)
    db.commit()
    db.refresh(item)
    return _category_out(db, item)


@router.post('/{area_id}/categories', response_model=CategoryOut, status_code=201, dependencies=[Depends(require_permission('areas:manage'))])
def create_or_link_category(area_id: int, payload: CategoryCreate, db: Session = Depends(get_db)):
    _ensure_category_catalog(db)
    area = _area(db, area_id)
    category = db.scalar(select(ExpenseCategoryCatalog).where(
        func.lower(ExpenseCategoryCatalog.name) == payload.name.lower()
    ))
    if not category:
        category = ExpenseCategoryCatalog(
            code=_unique_category_code(db, payload.name),
            name=payload.name,
            active=True,
        )
        db.add(category)
        db.flush()
    _link_category(db, area, category)
    db.commit()
    db.refresh(category)
    return _category_out(db, category)


@router.post('/{area_id}/categories/{category_id}', response_model=AreaOut, dependencies=[Depends(require_permission('areas:manage'))])
def link_existing_category(area_id: int, category_id: int, db: Session = Depends(get_db)):
    area = _area(db, area_id)
    category = _category(db, category_id)
    _link_category(db, area, category)
    db.commit()
    return _area_out(db, area, include_inactive=True)


@router.delete('/{area_id}/categories/{category_id}', response_model=AreaOut, dependencies=[Depends(require_permission('areas:manage'))])
def unlink_category(area_id: int, category_id: int, db: Session = Depends(get_db)):
    area = _area(db, area_id)
    category = _category(db, category_id)
    link = db.scalar(select(AreaCategoryLink).where(
        AreaCategoryLink.area_id == area.id,
        AreaCategoryLink.category_id == category.id,
    ))
    if not link:
        raise HTTPException(status_code=404, detail='La categoría no está habilitada para esta área')
    db.delete(link)
    legacy = db.scalar(select(ExpenseSubcategory).where(
        ExpenseSubcategory.area_id == area.id,
        ExpenseSubcategory.code == category.code,
    ))
    if legacy:
        legacy.active = False
    db.commit()
    return _area_out(db, area, include_inactive=True)


@router.patch('/categories/{category_id}', response_model=CategoryOut, dependencies=[Depends(require_permission('areas:manage'))])
def update_category(category_id: int, payload: CategoryUpdate, db: Session = Depends(get_db)):
    item = _category(db, category_id)
    changes = payload.model_dump(exclude_unset=True)
    if 'name' in changes:
        duplicate = db.scalar(select(ExpenseCategoryCatalog.id).where(
            func.lower(ExpenseCategoryCatalog.name) == changes['name'].lower(),
            ExpenseCategoryCatalog.id != item.id,
        ))
        if duplicate:
            raise HTTPException(status_code=409, detail='Ya existe una categoría con ese nombre')
        item.name = changes['name'].strip()
    if 'active' in changes:
        item.active = changes['active']
    for legacy in db.scalars(select(ExpenseSubcategory).where(
        ExpenseSubcategory.code == item.code
    )).all():
        legacy.name = item.name
        legacy.active = item.active
    db.commit()
    db.refresh(item)
    return _category_out(db, item)