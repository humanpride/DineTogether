import asyncio
from datetime import datetime

from core.celery_app import celery_app
from core.database import session_maker
from crud import booking_crud
from services.mail.notification_service import notification_service


@celery_app.task
def send_booking_created_to_user(
    email: str | None,
    user_name: str,
    venue_name: str,
    booking_time: str,
) -> None:
    """Уведомление пользователя о создании бронирования."""
    if not email:
        return
    asyncio.run(
        notification_service.send_notification(
            recipient=email,
            subject='Бронирование успешно создано',
            template_name='booking_created.html',
            user_name=user_name,
            venue_name=venue_name,
            booking_time=booking_time,
        ),
    )


@celery_app.task
def send_booking_created_to_managers(
    venue_name: str,
    user_name: str,
    user_email: str | None,
    booking_time: str,
    managers_emails: list[str | None],
) -> None:
    """Уведомление менеджеров о новом бронировании."""
    for email in managers_emails:
        if not email:
            continue
        asyncio.run(
            notification_service.send_notification(
                recipient=email,
                subject='Новое бронирование',
                template_name='admin_notification.html',
                user_name=user_name,
                user_email=user_email if user_email else 'Not provided',
                venue_name=venue_name,
                booking_time=booking_time,
            ),
        )


@celery_app.task
def send_booking_updated_to_managers(
    manager_emails: list[str | None],
    user_name: str,
    user_email: str | None,
    venue_name: str,
    booking_time: str,
) -> None:
    """Уведомление менеджеров об изменении бронирования."""
    for email in manager_emails:
        if not email:
            continue
        asyncio.run(
            notification_service.send_notification(
                recipient=email,
                subject='Бронирование изменено',
                template_name='booking_updated.html',
                user_name=user_name,
                user_email=user_email if user_email else 'Not provided',
                venue_name=venue_name,
                booking_time=booking_time,
            ),
        )


@celery_app.task
def send_booking_reminder(
    booking_id: int,
    email: str,
    template_name: str,
    user_name: str,
    venue_name: str,
    booking_time: str,
    expected_start_utc: datetime,
) -> None:
    """Send a booking reminder if the booking time is still current."""
    asyncio.run(
        _send_booking_reminder(
            booking_id=booking_id,
            email=email,
            template_name=template_name,
            user_name=user_name,
            venue_name=venue_name,
            booking_time=booking_time,
            expected_start_utc=expected_start_utc,
        ),
    )


async def _send_booking_reminder(
    booking_id: int,
    email: str,
    template_name: str,
    user_name: str,
    venue_name: str,
    booking_time: str,
    expected_start_utc: datetime,
) -> None:
    """Load the booking and send the reminder if it is still current."""
    async with session_maker() as session:
        booking = await booking_crud.get(
            booking_id=booking_id,
            session=session,
        )

        if booking is None or not booking.tables_slots:
            return

        actual_start = booking.tables_slots[0].booking_start_utc

        if actual_start != expected_start_utc:
            return

        await notification_service.send_notification(
            recipient=email,
            subject='Booking reminder',
            template_name=template_name,
            user_name=user_name,
            venue_name=venue_name,
            booking_time=booking_time,
        )
