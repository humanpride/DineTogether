import asyncio

from celery import shared_task

from services.mail.notification_service import (
    notification_service,
)


@shared_task
def send_booking_created_to_user(
    email: str,
    user_name: str,
    cafe_name: str,
    booking_time: str,
) -> None:
    """Уведомление пользователя о создании бронирования."""
    asyncio.run(
        notification_service.send_notification(
            recipient=email,
            subject='Бронирование успешно создано',
            template_name='booking_created.html',
            user_name=user_name,
            cafe_name=cafe_name,
            booking_time=booking_time,
        ),
    )


@shared_task
def send_booking_created_to_managers(
    cafe_name: int,
    user_name: str,
    booking_time: str,
    managers_emails: list[str],
) -> None:
    """Уведомление менеджеров о новом бронировании."""
    for email in managers_emails:
        asyncio.run(
            notification_service.send_notification(
                recipient=email,
                subject='Новое бронирование',
                template_name='admin_notification.html',
                user_name=user_name,
                cafe_name=cafe_name,
                booking_time=booking_time,
            ),
        )


@shared_task
def send_booking_updated_to_managers(
    manager_emails: list[str],
    user_name: str,
    cafe_name: str,
    booking_time: str,
) -> None:
    """Уведомление менеджеров об изменении бронирования."""
    for manager_email in manager_emails:
        asyncio.run(
            notification_service.send_notification(
                recipient=manager_email,
                subject='Бронирование изменено',
                template_name='booking_updated.html',
                user_name=user_name,
                cafe_name=cafe_name,
                booking_time=booking_time,
            ),
        )


@shared_task
def send_booking_reminder(
    email: str,
    template_name: str,
    user_name: str,
    cafe_name: str,
    booking_time: str,
) -> str:
    """Напоминание о бронирование (за час до бронирования)."""
    asyncio.run(
        notification_service.send_notification(
            recipient=email,
            subject='Напоминание о бронировании',
            template_name=template_name,
            user_name=user_name,
            cafe_name=cafe_name,
            booking_time=booking_time,
        ),
    )
