import re
from pydantic import BaseModel, Field, field_validator


class CleanName(BaseModel):
    name: str = Field(min_length=2, max_length=150)

    @field_validator('name', mode='before')
    @classmethod
    def clean_and_validate_name(cls, value):
        cleaned = re.sub(r'\s+', ' ', str(value or '').strip())
        parts = [part.strip() for part in cleaned.split('/')]
        valid_part = r'[^\W\d_]+(?: [^\W\d_]+)*'
        if not parts or any(
            not part or not re.fullmatch(valid_part, part, flags=re.UNICODE)
            for part in parts
        ):
            raise ValueError(
                'Solo se permiten letras, espacios y / como separador; las tildes y la ñ están permitidas'
            )
        return ' / '.join(parts)


class CategoryCreate(CleanName):
    pass


class CategoryOut(BaseModel):
    id: int
    code: str
    name: str
    active: bool
    area_ids: list[int] = []

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


class CategoryUpdate(AreaUpdate):
    pass


class AreaOut(BaseModel):
    id: int
    code: str
    name: str
    active: bool
    categories: list[CategoryOut]

    class Config:
        from_attributes = True
