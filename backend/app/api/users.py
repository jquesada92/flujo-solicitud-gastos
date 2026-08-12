import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password, normalize_email, require_permission
from app.models.entities import User, UserRole
from app.schemas.user import UserCreate, UserOut, UserUpdate
from app.services.email_service import send_user_invitation

router = APIRouter(dependencies=[Depends(require_permission('can_configure'))])


@router.get('', response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)):
    return list(db.scalars(select(User).order_by(User.name)).all())


@router.post('', response_model=UserOut, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    email = normalize_email(str(payload.email))
    if db.scalar(select(User.id).where(func.lower(User.email) == email)):
        raise HTTPException(status_code=409, detail='Ya existe un usuario con ese correo')
    defaults = {
        UserRole.REQUESTER: (True, False, True, False),
        UserRole.APPROVER: (False, True, True, False),
        UserRole.VIEWER: (False, False, True, False),
        UserRole.ADMIN: (True, True, True, True),
    }[payload.role]
    temporary_password = secrets.token_urlsafe(15)
    user = User(name=payload.name.strip(), email=email, password_hash=hash_password(temporary_password), role=payload.role,
                can_request=payload.can_request if payload.can_request is not None else defaults[0],
                can_approve=payload.can_approve if payload.can_approve is not None else defaults[1],
                can_view=payload.can_view if payload.can_view is not None else defaults[2],
                can_configure=payload.can_configure if payload.can_configure is not None else defaults[3],
                must_change_password=True)
    db.add(user)
    try:
        db.flush()
        send_user_invitation(user, temporary_password)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail='No se pudo enviar la invitación. El usuario no fue creado.') from exc
    db.refresh(user)
    return user


@router.patch('/{user_id}', response_model=UserOut)
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail='Usuario no encontrado')
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(user, key, value.strip() if key == 'name' else value)
    db.commit()
    db.refresh(user)
    return user
