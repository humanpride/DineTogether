from datetime import time
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Text, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.base_model import Base
from core.constants import SLOT_TIME_FORMAT

if TYPE_CHECKING:
    from models import Venue


class TimeSlot(Base):
    """Represent an available booking time interval for a venue."""

    venue_id: Mapped[int] = mapped_column(
        ForeignKey(
            'venues.id',
            ondelete='CASCADE',
        ),
        nullable=False,
        comment='Venue ID',
    )
    start_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
        comment='Slot start time',
    )
    end_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
        comment='Slot end time',
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment='Slot descriprion',
    )
    venue: Mapped['Venue'] = relationship(lazy='selectin')

    __table_args__ = (
        CheckConstraint(
            'end_time > start_time',
            name='check_time_order',
        ),
        UniqueConstraint(
            'venue_id',
            'start_time',
            'end_time',
            name='uq_venue_timeslot',
        ),
    )

    def __repr__(self) -> str:
        """Return the string representation of the TimeSlot instance."""
        return (
            f'<{self.__class__.__name__}('
            f'id={self.id}, '
            f'venue_id={self.venue_id}, '
            f'start_time={self.start_time.strftime(SLOT_TIME_FORMAT)}, '
            f'end_time={self.end_time.strftime(SLOT_TIME_FORMAT)})>'
        )
