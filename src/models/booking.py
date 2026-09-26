from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.base_model import Base
from core.constants import BookingStatus

if TYPE_CHECKING:
    from .slot import TimeSlot
    from .table import Table
    from .user import User
    from .venue import Venue


class Booking(Base):
    """Represent a user's reservation containing selected tables and time slots."""

    user_id: Mapped[int] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
    )
    venue_id: Mapped[int] = mapped_column(
        ForeignKey('venues.id', ondelete='CASCADE'),
        nullable=False,
    )
    booking_date: Mapped[date] = mapped_column(Date, nullable=False)
    guest_number: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus, name='booking_status'),
        default=BookingStatus.BOOKING,
        server_default=BookingStatus.BOOKING.value,
        nullable=False,
    )

    # relationships
    user: Mapped['User'] = relationship('User', lazy='selectin')
    venue: Mapped['Venue'] = relationship('Venue', lazy='selectin')
    tables_slots: Mapped[list['BookingTableSlot']] = relationship(
        'BookingTableSlot',
        back_populates='booking',
        cascade='all, delete-orphan',
        lazy='raise',
    )


class BookingTableSlot(Base):
    """Represent a reserved table for a specific booking time slot."""

    __tablename__ = 'booking_table_slots'

    booking_id: Mapped[int] = mapped_column(
        ForeignKey('bookings.id', ondelete='CASCADE'),
        nullable=False,
    )
    table_id: Mapped[int] = mapped_column(
        ForeignKey('tables.id', ondelete='CASCADE'),
        nullable=False,
    )
    slot_id: Mapped[int] = mapped_column(
        ForeignKey('timeslots.id', ondelete='CASCADE'),
        nullable=False,
    )
    booking_start_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    booking_end_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # relationships
    booking: Mapped['Booking'] = relationship('Booking', back_populates='tables_slots')
    table: Mapped['Table'] = relationship('Table', lazy='selectin')
    slot: Mapped['TimeSlot'] = relationship('TimeSlot', lazy='selectin')

    __table_args__ = (
        UniqueConstraint(
            'booking_id',
            'table_id',
            'slot_id',
            name='uq_booking_table_slot',
        ),
    )
