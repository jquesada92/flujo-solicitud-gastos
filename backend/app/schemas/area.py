import re
from pydantic import BaseModel, Field, field_validator


class CleanName(BaseModel):
    name: str = Field(min_length=2, max_length=150)

    @field_validator('name', mode='before')
    @classmethod
    def clean_and_validate_name(cls, value):
        cleaned = re.sub(r'\s+', ' ', str(value or '').strip())
        if not re.fullmatch(r'[^\W\d_]+(?: [^\W\d_]+)*', cleaned, flags=re.UNICODE):
            raise ValueError('Solo se permiten letras y espacios; las tildes y la ñ están permitidas')
        return cleaned


class SubcategoryCreate(CleanName):
    pass


class SubcategoryOut(BaseModel):
    id: int
    code: str
    name: str
    active: bool

    class Config:
        from_attributes = True


class AreaCreate(CleanName):
    pass


class AreaUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    active: bool | None = None

    @field_validator('name', mode='before')
    @classmethod
    def clean_optional_name(cls, value):
        if value is None:
            return value
        return CleanName(name=value).name


class AreaOut(BaseModel):
    id: int
    code: str
    name: str
    active: bool
    subcategories: list[SubcategoryOut]

    class Config:
        from_attributes = True
