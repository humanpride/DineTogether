from typing import TYPE_CHECKING

from sqlalchemy import UUID, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.base_model import Base
from models.dish import dish_cafe_association

if TYPE_CHECKING:
    from .dish import Dish
    from .user import User


class Cafe(Base):
    """Модель кафе с контактной информацией и описанием."""

    name: Mapped[str] = mapped_column(String(255), unique=True)
    address: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(
        String(20),
        unique=True,
        nullable=True,
    )
    description: Mapped[str] = mapped_column(Text, nullable=True)
    photo_id: Mapped[UUID | None] = mapped_column(
        ForeignKey('media_files.id', ondelete='SET NULL'),
        nullable=True,
    )
    dishes: Mapped[list['Dish'] | None] = relationship(
        secondary=dish_cafe_association,
        back_populates='cafes',
        lazy='raise',
    )
    managers: Mapped[list['User']] = relationship(back_populates='cafe', lazy='raise')

    __table_args__ = (
        UniqueConstraint(
            'name',
            'address',
            name='cafe_name_address',
        ),
    )
