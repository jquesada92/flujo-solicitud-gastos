from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_token, current_user, hash_password, normalize_email, verify_password
from app.models.entities import User
from app.schemas.user import ChangePasswordRequest, LoginRequest, UserOut

router = APIRouter()


@router.post('/login')
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    email = normalize_email(str(payload.email))
    user = db.scalar(select(User).where(func.lower(User.email) == email))
    if not user or not user.active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail='Correo o contraseña incorrectos')
    return {'access_token': create_token(user), 'token_type': 'bearer', 'user': UserOut.model_validate(user)}


@router.get('/me', response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user


@router.post('/change-password')
def change_password(payload: ChangePasswordRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail='La contraseña temporal no es correcta')
    if payload.current_password == payload.new_password:
        raise HTTPException(status_code=400, detail='La nueva contraseña debe ser diferente a la temporal')
    user.password_hash = hash_password(payload.new_password)
    user.must_change_password = False
    db.commit()
    db.refresh(user)
    return {'access_token': create_token(user), 'token_type': 'bearer', 'user': UserOut.model_validate(user)}
