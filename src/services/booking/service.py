from datetime import date
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.validators import (
    validate_booking_conflicts,
    validate_booking_date,
    validate_booking_slots,
    validate_booking_tables,
)
from crud import booking_crud
from models import Booking, BookingTableSlot, TimeSlot, Venue
from schemas.booking import (
    BookingCreate,
    BookingTableSlotSchema,
    BookingUpdate,
)
from services.booking.datetime import build_booking_interval, utc_to_local
from services.booking.scheduler import (
    reschedule_booking_reminders,
    schedule_booking_reminders,
)
from tasks.email import (
    send_booking_created_to_managers,
    send_booking_created_to_user,
    send_booking_updated_to_managers,
)


class BookingService:
    """Handle booking business logic."""

    async def create_booking(
        self,
        booking_in: BookingCreate,
        user_id: int,
        session: AsyncSession,
    ) -> Booking:
        """Create a booking and schedule its reminders."""
        await validate_booking_date(booking_date=booking_in.booking_date)

        stmt = select(Venue).options(selectinload(Venue.managers)).where(Venue.id == booking_in.venue_id)

        venue = await session.scalar(stmt)
        if venue is None:
            raise ValueError(
                f'Venue with id={booking_in.venue_id} does not exist.',
            )

        if not booking_in.tables_slots and isinstance(booking_in, BookingCreate):
            raise ValueError('At least one table and one slot must be selected.')

        await validate_booking_tables(
            table_ids=[item.table_id for item in booking_in.tables_slots],
            venue_id=venue.id,
            session=session,
        )

        slots = await validate_booking_slots(
            slot_ids=[item.slot_id for item in booking_in.tables_slots],
            venue=venue,
            booking_date=booking_in.booking_date,
            session=session,
        )

        booking_table_slots = self._build_booking_table_slots(
            booking_date=booking_in.booking_date,
            tables_slots=booking_in.tables_slots,
            slots_by_id={slot.id: slot for slot in slots},
            timezone_name=venue.timezone,
        )

        await validate_booking_conflicts(
            tables_slots=booking_table_slots,
            guest_number=booking_in.guest_number,
            session=session,
        )

        booking = Booking(
            user_id=user_id,
            venue_id=venue.id,
            guest_number=booking_in.guest_number,
            note=booking_in.note,
            booking_date=booking_in.booking_date,
        )
        booking.tables_slots = booking_table_slots

        await booking_crud.create(
            booking=booking,
            session=session,
        )

        await session.commit()

        booking = await booking_crud.get(
            booking_id=booking.id,
            session=session,
        )

        booking_start_utc = booking.tables_slots[0].booking_start_utc
        formatted_local_time = utc_to_local(
            utc_datetime=booking_start_utc,
            timezone_name=venue.timezone,
        ).strftime('%d.%m.%Y %H:%M')

        send_booking_created_to_user.delay(
            email=booking.user.email,
            user_name=booking.user.username,
            venue_name=venue.name,
            booking_time=formatted_local_time,
        )
        send_booking_created_to_managers.delay(
            venue_name=venue.name,
            user_name=booking.user.username,
            user_email=booking.user.email,
            booking_time=formatted_local_time,
            managers_emails=[manager.email for manager in venue.managers],
        )

        schedule_booking_reminders(booking, booking_start_utc, formatted_local_time)

        return booking

    async def update_booking(
        self,
        booking: Booking,
        booking_in: BookingUpdate,
        session: AsyncSession,
    ) -> Booking:
        """Update a booking and reschedule its reminders when necessary."""
        stmt = select(Venue).options(selectinload(Venue.managers)).where(Venue.id == booking.venue_id)
        venue = await session.scalar(stmt)
        new_booking_date = (
            booking_in.booking_date if booking_in.booking_date is not None else booking.booking_date
        )

        await validate_booking_date(booking_date=new_booking_date)

        time_changed = booking_in.booking_date is not None or booking_in.tables_slots is not None

        if booking_in.tables_slots is not None:
            tables_slots = booking_in.tables_slots
        else:
            tables_slots = [
                BookingTableSlotSchema(
                    table_id=item.table_id,
                    slot_id=item.slot_id,
                )
                for item in booking.tables_slots
            ]

        if time_changed:
            await validate_booking_tables(
                table_ids=[item.table_id for item in tables_slots],
                venue_id=booking.venue_id,
                session=session,
            )
            slots = await validate_booking_slots(
                slot_ids=[item.slot_id for item in tables_slots],
                venue=venue,
                booking_date=booking_in.booking_date if booking_in.booking_date else booking.booking_date,
                session=session,
            )

            new_table_slots = self._build_booking_table_slots(
                booking_date=new_booking_date,
                tables_slots=tables_slots,
                slots_by_id={slot.id: slot for slot in slots},
                timezone_name=venue.timezone,
            )
        else:
            new_table_slots = booking.tables_slots

        new_guest_number = (
            booking_in.guest_number if booking_in.guest_number is not None else booking.guest_number
        )

        await validate_booking_conflicts(
            tables_slots=new_table_slots,
            guest_number=new_guest_number,
            session=session,
            booking_id=booking.id,
        )

        update_data = booking_in.model_dump(
            exclude={'tables_slots'},
            exclude_unset=True,
        )

        for field, value in update_data.items():
            setattr(booking, field, value)

        if time_changed:
            booking.tables_slots = new_table_slots

        await booking_crud.update(
            booking=booking,
            session=session,
        )

        await session.commit()

        booking = await booking_crud.get(
            booking_id=booking.id,
            session=session,
        )

        booking_start_utc = booking.tables_slots[0].booking_start_utc
        formatted_local_time = utc_to_local(
            utc_datetime=booking_start_utc,
            timezone_name=venue.timezone,
        ).strftime('%d.%m.%Y %H:%M')

        send_booking_updated_to_managers(
            manager_emails=[manager.email for manager in venue.managers],
            user_name=booking.user.username,
            user_email=booking.user.email,
            venue_name=venue.name,
            booking_time=formatted_local_time,
        )

        if time_changed:
            reschedule_booking_reminders(booking, booking_start_utc, formatted_local_time)

        return booking

    @staticmethod
    def _build_booking_table_slots(
        booking_date: date,
        tables_slots: Sequence[BookingTableSlotSchema],
        slots_by_id: dict[int, TimeSlot],
        timezone_name: str,
    ) -> list[BookingTableSlot]:
        """Build booking table-slot entities with UTC intervals."""
        booking_table_slots = []

        for item in tables_slots:
            slot = slots_by_id[item.slot_id]

            booking_start_utc, booking_end_utc = build_booking_interval(
                booking_date=booking_date,
                slot=slot,
                timezone_name=timezone_name,
            )

            booking_table_slots.append(
                BookingTableSlot(
                    table_id=item.table_id,
                    slot_id=item.slot_id,
                    booking_start_utc=booking_start_utc,
                    booking_end_utc=booking_end_utc,
                ),
            )

        return sorted(booking_table_slots, key=lambda item: item.booking_start_utc)


booking_service = BookingService()
