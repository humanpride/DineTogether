from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from core.base_model import get_utc_now
from crud.venue import venue_crud
from models.booking import Booking
from tasks.email import (
    send_booking_created_to_managers,
    send_booking_created_to_user,
    send_booking_reminder,
)


async def handle_booking_created(
    booking: Booking,
    session: AsyncSession,
    updated: bool = False,
) -> None:
    """Отправляет уведомления после создания бронирования."""
    slot = booking.tables_slots[0].slot

    booking_datetime = datetime.combine(
        booking.booking_date,
        slot.start_time,
    )

    booking_time = booking_datetime.strftime(
        '%d.%m.%Y %H:%M',
    )

    await session.refresh(booking.venue, attribute_names=['managers'])

    # TODO: Сделать логику обновления напоминаний, если изменилось время бронирования
    if updated:
        ...

    send_booking_created_to_user.delay(
        email=booking.user.email,
        user_name=booking.user.username,
        venue_name=booking.venue.name,
        booking_time=booking_time,
    )

    send_booking_created_to_managers.delay(
        venue_name=booking.venue.name,
        user_name=booking.user.username,
        user_email=booking.user.email,
        booking_time=booking_time,
        managers_emails=await venue_crud.get_managers_emails(booking.venue, session),
    )

    reminders = [
        (
            booking_datetime - timedelta(days=1),
            'booking_day_reminder.html',
        ),
        (
            booking_datetime - timedelta(hours=1),
            'booking_reminder.html',
        ),
    ]
    for reminder_time, template_name in reminders:
        # FIXME: сравниваются offset-naive и offset-aware datetime. Нужно привести к виду.
        if reminder_time > get_utc_now():
            send_booking_reminder.apply_async(
                kwargs={
                    'email': booking.user.email,
                    'template_name': template_name,
                    'user_name': booking.user.username,
                    'venue_name': booking.venue.name,
                    'booking_time': booking_time,
                },
                eta=reminder_time,
            )
