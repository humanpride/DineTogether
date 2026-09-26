from datetime import UTC, date, datetime, time
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from models import TimeSlot

if TYPE_CHECKING:
    from models import TimeSlot


def utc_to_local(
    utc_datetime: datetime,
    timezone_name: str,
) -> datetime:
    """Convert UTC datetime to venue local time."""
    return utc_datetime.astimezone(
        ZoneInfo(timezone_name),
    )


def _get_valid_local_datetimes(
    local_datetime: datetime,
) -> list[datetime]:
    """Return valid interpretations of a local datetime."""
    timezone = local_datetime.tzinfo
    if timezone is None:
        raise ValueError('Local datetime must be timezone-aware.')

    valid_datetimes = []

    for fold in (0, 1):
        candidate = local_datetime.replace(fold=fold)

        utc_datetime = candidate.astimezone(UTC)
        roundtrip = utc_datetime.astimezone(timezone)

        if roundtrip.replace(tzinfo=None) == local_datetime.replace(tzinfo=None) and roundtrip.fold == fold:
            valid_datetimes.append(candidate)

    return valid_datetimes


def local_to_utc(
    booking_date: date,
    booking_time: time,
    timezone_name: str,
) -> datetime:
    """Convert a local date and time to an unambiguous UTC datetime."""
    timezone = ZoneInfo(timezone_name)

    local_datetime = datetime.combine(
        booking_date,
        booking_time,
        tzinfo=timezone,
    )

    valid_datetimes = _get_valid_local_datetimes(local_datetime)

    if not valid_datetimes:
        raise ValueError(
            f'The local time {booking_date} {booking_time} does not exist in timezone {timezone_name}.',
        )

    if len(valid_datetimes) > 1:
        raise ValueError(
            f'The local time {booking_date} {booking_time} is ambiguous in timezone {timezone_name}.',
        )

    return valid_datetimes[0].astimezone(UTC)


def build_booking_interval(
    booking_date: date,
    slot: 'TimeSlot',
    timezone_name: str,
) -> tuple[datetime, datetime]:
    """Build an unambiguous UTC booking interval."""
    return (
        local_to_utc(
            booking_date,
            slot.start_time,
            timezone_name,
        ),
        local_to_utc(
            booking_date,
            slot.end_time,
            timezone_name,
        ),
    )
