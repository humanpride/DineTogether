from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.base_model import Base

if TYPE_CHECKING:
    from models.venue import Venue


class Table(Base):
    """Represent a venue table with its seating capacity and details."""

    venue_id: Mapped[int] = mapped_column(ForeignKey('venues.id'))
    seat_number: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    venue: Mapped['Venue'] = relationship(lazy='selectin')
