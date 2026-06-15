from typing import TYPE_CHECKING

from sqlalchemy import UUID, Column, Float, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.base_model import Base

if TYPE_CHECKING:
    from .cafe import Cafe

dish_cafe_association = Table(
    'dish_cafe_association',
    Base.metadata,
    Column(
        'dish_id',
        ForeignKey('dishes.id', ondelete='CASCADE'),
        primary_key=True,
    ),
    Column(
        'cafe_id',
        ForeignKey('cafes.id', ondelete='CASCADE'),
        primary_key=True,
    ),
)


class Dish(Base):
    """Модель блюда в меню."""

    __tablename__ = 'dishes'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Float)

    photo_id: Mapped[UUID | None] = mapped_column(
        ForeignKey('media_files.id', ondelete='SET NULL'),
        nullable=True,
    )

    cafes: Mapped[list['Cafe'] | None] = relationship(
        secondary=dish_cafe_association,
        back_populates='dishes',
        lazy='raise',
    )
