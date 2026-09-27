from datetime import datetime, timedelta

from core.base_model import get_utc_now
from models import Booking
from tasks.email import (
    send_booking_reminder,
)

REMINDER_SCHEDULE = (
    (
        timedelta(days=1),
        'booking_day_reminder.html',
    ),
    (
        timedelta(hours=1),
        'booking_reminder.html',
    ),
)


def schedule_booking_reminders(
    booking: Booking,
    booking_start_utc: datetime,
    formatted_local_time: str,
) -> None:
    """Schedule reminders for a booking."""
    if not booking.tables_slots:
        raise ValueError(
            f'Booking {booking.id} has no table-slot assignments.',
        )

    for offset, template_name in REMINDER_SCHEDULE:
        reminder_at = booking_start_utc - offset

        if reminder_at <= get_utc_now():
            continue

        send_booking_reminder.apply_async(  # type: ignore[attr-defined]
            args=(
                booking.id,
                booking.user.email,
                template_name,
                booking.user.username,
                booking.venue.name,
                formatted_local_time,
                booking_start_utc,
            ),
            eta=reminder_at,
        )


def reschedule_booking_reminders(
    booking: Booking,
    booking_start_utc: datetime,
    formatted_local_time: str,
) -> None:
    """Schedule reminders for an updated booking."""
    schedule_booking_reminders(booking, booking_start_utc, formatted_local_time)
