from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.base_model import Base

if TYPE_CHECKING:
    from models.cafe import Cafe


class Table(Base):
    """Модель стола."""

    cafe_id: Mapped[int] = mapped_column(ForeignKey('cafes.id'))
    seat_number: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    cafe: Mapped['Cafe'] = relationship(lazy='selectin')
