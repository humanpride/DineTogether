from typing import Any, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from crud.base import CRUDBase
from models import Booking, BookingTableSlot
from schemas.booking import (
    BookingCreate,
    BookingUpdate,
)


class CRUDBooking(CRUDBase[Booking, BookingCreate, BookingUpdate]):
    """CRUD для бронирований."""

    _get_statement = select(Booking).options(
        selectinload(Booking.user),
        selectinload(Booking.venue),
        selectinload(Booking.tables_slots).selectinload(BookingTableSlot.table),
        selectinload(Booking.tables_slots).selectinload(BookingTableSlot.slot),
    )

    async def get(self, booking_id: int, session: AsyncSession) -> Booking | None:
        """Получает бронирование с полной информацией по ID."""
        stmt = self._get_statement.where(Booking.id == booking_id)
        return await session.scalar(stmt)

    async def get_all(
        self,
        session: AsyncSession,
        **filters: Any,
    ) -> Sequence[Booking]:
        """Получает список бронирований с фильтрацией."""
        stmt = self._get_statement
        for field, value in filters.items():
            if value is not None:
                stmt = stmt.where(getattr(Booking, field) == value)
        return (await session.scalars(stmt)).all()

    async def create(
        self,
        booking: Booking,
        session: AsyncSession,
    ) -> Booking:
        """Create booking entry in database.

        Args:
            booking (Booking): reservation data
            session (AsyncSession): current db session

        Returns:
            Booking: Booking data after the database record is created.

        """
        session.add(booking)

        await session.flush()

        return booking

    async def update(
        self,
        booking: Booking,
        session: AsyncSession,
    ) -> Booking:
        """Update booking entry in database.

        Args:
            booking (Booking): new booking data
            session (AsyncSession): current db session

        Returns:
            Booking: Booking data after the database record is updated.

        """
        session.add(booking)

        await session.flush()

        return booking


booking_crud = CRUDBooking(Booking)
