from typing import TYPE_CHECKING, Any, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from crud.base import CRUDBase
from models import Booking, BookingTableSlot
from schemas.booking import (
    BookingCreate,
    BookingInfo,
    BookingTableSlotSchema,
    BookingUpdate,
)

if TYPE_CHECKING:
    from models.user import User


class CRUDBooking(CRUDBase[Booking, BookingCreate, BookingUpdate]):
    """CRUD для бронирований."""

    _get_statement = select(Booking).options(
        selectinload(Booking.user),
        selectinload(Booking.cafe),
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
        obj_in: BookingCreate,
        user_id: int,
        session: AsyncSession,
    ) -> Booking:
        """Создает бронирование и связи с выбранными столами и слотами."""
        booking = Booking(
            user_id=user_id,
            cafe_id=obj_in.cafe_id,
            guest_number=obj_in.guest_number,
            note=obj_in.note,
            booking_date=obj_in.booking_date,
        )

        session.add(booking)

        await session.flush()

        await self._create_or_replace_tables_slots(
            booking=booking,
            tables_slots=obj_in.tables_slots,
            session=session,
        )
        return booking

    async def update(
        self,
        booking: Booking,
        obj_in: BookingUpdate,
        user: 'User',
        session: AsyncSession,
    ) -> BookingInfo:
        """Обновляет бронирование и уведомляет менеджеров."""
        update_data = obj_in.model_dump(
            exclude={'tables_slots'},
            exclude_unset=True,
        )

        for field, value in update_data.items():
            setattr(booking, field, value)

        if obj_in.tables_slots is not None:
            booking.tables_slots.clear()

            await session.flush()

            booking.tables_slots.extend(
                BookingTableSlot(
                    table_id=item.table_id,
                    slot_id=item.slot_id,
                )
                for item in obj_in.tables_slots
            )

        session.add(booking)

        await session.flush()

        return booking

    async def _create_or_replace_tables_slots(
        self,
        booking: Booking,
        tables_slots: list[BookingTableSlotSchema],
        session: AsyncSession,
    ) -> None:
        """Создает или заменяет набор столов и слотов у бронирования."""
        booking_tables_slots = [
            BookingTableSlot(
                booking_id=booking.id,
                table_id=item.table_id,
                slot_id=item.slot_id,
            )
            for item in tables_slots
        ]

        session.add_all(booking_tables_slots)

        await session.flush()


booking_crud = CRUDBooking(Booking)
