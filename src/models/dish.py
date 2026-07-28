from typing import TYPE_CHECKING

from sqlalchemy import UUID, Column, Float, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.base_model import Base

if TYPE_CHECKING:
    from .venue import Venue

dish_venue_association = Table(
    'dish_venue_association',
    Base.metadata,
    Column(
        'dish_id',
        ForeignKey('dishes.id', ondelete='CASCADE'),
        primary_key=True,
    ),
    Column(
        'venue_id',
        ForeignKey('venues.id', ondelete='CASCADE'),
        primary_key=True,
    ),
)


class Dish(Base):
    """Represent a menu item that can be offered by multiple venues."""

    __tablename__ = 'dishes'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Float)

    photo_id: Mapped[UUID | None] = mapped_column(
        ForeignKey('media_files.id', ondelete='SET NULL'),
        nullable=True,
    )

    venues: Mapped[list['Venue'] | None] = relationship(
        secondary=dish_venue_association,
        back_populates='dishes',
        lazy='raise',
    )
