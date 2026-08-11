from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_token, current_user, normalize_email, verify_password
from app.models.entities import User
from app.schemas.user import LoginRequest, UserOut

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
