from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ExpenseCategoryCatalog(Base):
    __tablename__ = 'expense_category_catalog'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class AreaCategoryLink(Base):
    __tablename__ = 'expense_area_categories'
    __table_args__ = (UniqueConstraint('area_id', 'category_id', name='uq_expense_area_category'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    area_id: Mapped[int] = mapped_column(
        ForeignKey('expense_categories.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey('expense_category_catalog.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
