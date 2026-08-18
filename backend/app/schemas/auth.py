from typing import Literal

from pydantic import BaseModel

from app.schemas.user import UserOut


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal['bearer'] = 'bearer'


class LoginResponse(TokenResponse):
    user: UserOut
