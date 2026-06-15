from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from crud.cafe import cafe_crud
from models.booking import Booking
from tasks.email import (
    send_booking_created_to_managers,
    send_booking_created_to_user,
    send_booking_reminder,
)


async def handle_booking_created(
    booking: Booking,
    session: AsyncSession,
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

    send_booking_created_to_user.delay(
        email=booking.user.email,
        user_name=booking.user.username,
        cafe_name=booking.cafe.name,
        booking_time=booking_time,
    )

    await session.refresh(booking.cafe, attribute_names=['managers'])
    send_booking_created_to_managers.delay(
        cafe_name=booking.cafe.name,
        user_name=booking.user.username,
        booking_time=booking_time,
        managers_emails=await cafe_crud.get_managers_emails(booking.cafe, session),
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
    for eta, template_name in reminders:
        if eta > datetime.utcnow():
            send_booking_reminder.apply_async(
                kwargs={
                    'email': booking.user.email,
                    'template_name': template_name,
                    'user_name': booking.user.username,
                    'cafe_name': booking.cafe.name,
                    'booking_time': booking_time,
                },
                eta=eta,
            )
