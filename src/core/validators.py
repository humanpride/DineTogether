import logging
from datetime import date, time
from typing import Any, Optional, Sequence

from PIL import Image, UnidentifiedImageError
from fastapi import HTTPException, UploadFile, status
from pydantic import EmailStr
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.base_model import get_utc_now
from core.constants import (
    ALLOWED_FORMATS,
    ALLOWED_MEDIA_CONTENT_TYPES,
    ALLOWED_MEDIA_EXTENSIONS,
    INVALID_IMAGE_FORMAT,
    INVALID_IMAGE_SIZE,
    MAX_MEDIA_SIZE,
    SLOT_TIME_FORMAT,
    BookingStatus,
    UserRole,
)
from core.dependencies import CurrentUserDep, SessionDep
from core.logging import log
from crud.user import user_crud
from crud.venue import venue_crud
from models import Booking, BookingTableSlot, Table, TimeSlot, User, Venue
from services.booking.datetime import local_to_utc


async def _validate_unique_field(
    field_name: str,
    field_value: Optional[Any],
    current_value: Optional[Any],
    user_id: Optional[int],
    session: AsyncSession,
    error_message: str,
) -> None:
    """Вспомогательная функция для проверки уникальности поля."""
    if not field_value:
        return
    if current_value is not None and field_value == current_value:
        return

    # Проверка существования в БД
    filters = {field_name: field_value}
    user = await user_crud.get_one_or_none(session=session, **filters)

    if user:
        if user_id and user.id == user_id:
            return
        # Пользователь с таким значением уже существует
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error_message,
        )


async def validate_unique_username(
    session: AsyncSession,
    username: Optional[str],
    current_username: Optional[str] = None,
    user_id: Optional[int] = None,
) -> None:
    """Проверяет уникальность username."""
    await _validate_unique_field(
        field_name='username',
        field_value=username,
        current_value=current_username,
        user_id=user_id,
        session=session,
        error_message='Пользователь с таким username уже существует',
    )


async def validate_unique_email(
    session: AsyncSession,
    email: Optional[EmailStr],
    current_email: Optional[EmailStr] = None,
    user_id: Optional[int] = None,
) -> None:
    """Проверяет уникальность email."""
    await _validate_unique_field(
        session=session,
        field_value=email,
        current_value=current_email,
        user_id=user_id,
        field_name='email',
        error_message='Пользователь с таким email уже существует',
    )


async def validate_unique_phone(
    session: AsyncSession,
    phone: Optional[str],
    current_phone: Optional[str] = None,
    user_id: Optional[int] = None,
) -> None:
    """Проверяет уникальность телефона."""
    await _validate_unique_field(
        session=session,
        field_value=phone,
        current_value=current_phone,
        user_id=user_id,
        field_name='phone',
        error_message='Пользователь с таким телефоном уже существует',
    )


async def validate_booking_tables(
    table_ids: Sequence[int],
    venue_id: int,
    session: AsyncSession,
) -> None:
    """Validate selected tables."""
    if not (unique_table_ids := set(table_ids)):
        raise ValueError('At least one table must be selected.')
    prepared_statement = select(Table.id).where(Table.id.in_(unique_table_ids))
    existing_table_ids = set(
        (
            await session.scalars(
                prepared_statement.where(Table.venue_id == venue_id),
            )
        ).all(),
    )
    if missing_tables := unique_table_ids - existing_table_ids:
        raise ValueError(f'Tables {missing_tables} are not belong to venue {venue_id}')

    inactive_table_ids = set(
        (
            await session.scalars(
                prepared_statement.where(Table.is_active.is_(False)),
            )
        ).all(),
    )
    if inactive_table_ids:
        raise ValueError(
            f'Tables {inactive_table_ids} are not available for reservation.',
        )


async def validate_booking_slots(
    slot_ids: Sequence[int],
    venue: Venue,
    booking_date: date,
    session: AsyncSession,
) -> Sequence[TimeSlot]:
    """Validate selected slots."""
    if not (unique_slot_ids := set(slot_ids)):
        raise ValueError('At least one time slot must be selected.')
    prepared_statement = select(TimeSlot).where(TimeSlot.id.in_(unique_slot_ids))

    slots = (
        await session.scalars(
            prepared_statement.where(TimeSlot.venue_id == venue.id),
        )
    ).all()

    existing_slot_ids = {slot.id for slot in slots}
    if missing_slots := unique_slot_ids - existing_slot_ids:
        raise ValueError(f'Slots {missing_slots} are not belong to venue {venue.id}')

    now = get_utc_now()
    if any(local_to_utc(booking_date, slot.start_time, venue.timezone) < now for slot in slots):
        raise ValueError('Cannot create a booking with slots in the past.')

    return slots


async def validate_booking_date(booking_date: date) -> None:
    """Проверяет, что дата бронирования не находится в прошлом."""
    if booking_date < date.today():
        raise ValueError(
            'Нельзя создать или изменить бронирование на прошедшую дату',
        )


async def validate_booking_conflicts(
    tables_slots: list[BookingTableSlot],
    guest_number: int,
    session: AsyncSession,
    booking_id: int | None = None,
) -> None:
    """Validate booking time conflicts and seating capacity.

    Ensures that:
    - selected tables are not occupied during overlapping time intervals;
    - the total seating capacity of the selected tables is sufficient.

    When updating a booking, the current booking is excluded from the
    conflict check.
    """
    if not tables_slots:
        return

    conflict_conditions = [
        and_(
            BookingTableSlot.table_id == item.table_id,
            BookingTableSlot.booking_start_utc < item.booking_end_utc,
            BookingTableSlot.booking_end_utc > item.booking_start_utc,
        )
        for item in tables_slots
    ]

    stmt = (
        select(BookingTableSlot.id)
        .join(
            Booking,
            Booking.id == BookingTableSlot.booking_id,
        )
        .where(
            or_(*conflict_conditions),
            Booking.status.in_(
                (
                    BookingStatus.BOOKING,
                    BookingStatus.ACTIVE,
                ),
            ),
        )
        .limit(1)
    )

    if booking_id is not None:
        stmt = stmt.where(Booking.id != booking_id)

    conflict = await session.scalar(stmt)

    if conflict is not None:
        raise ValueError(
            'One or more selected tables are already booked for the selected time interval.',
        )

    table_ids = {item.table_id for item in tables_slots}

    total_seats = await session.scalar(
        select(func.sum(Table.seat_number)).where(
            Table.id.in_(table_ids),
        ),
    )

    if guest_number > (total_seats or 0):
        raise ValueError(
            'The number of guests exceeds the seating capacity of the selected tables.',
        )


async def validate_unique_venue_name(
    venue_name: str,
    session: AsyncSession,
) -> None:
    """Проверяет уникальность названия кафе."""
    stmt = select(Venue).where(Venue.name == venue_name)

    existing_venue = await session.scalar(stmt)

    if existing_venue:
        raise ValueError(
            f'Кафе с названием "{venue_name}" уже существует',
        )


async def validate_venue_managers(
    manager_ids: list[int],
    session: AsyncSession,
    venue: Venue | None = None,
) -> None:
    """Валидация менеджеров кафе при создании или обновлении кафе.

    Проверяет, что:
    - для кафе указан хотя бы один менеджер;
    - все указанные пользователи существуют в базе данных;
    - у всех пользователей роль MANAGER и они активны;
    - ни один из менеджеров не привязан к другому кафе.
    """
    if not manager_ids:
        raise ValueError('У кафе должен быть хотя бы один менеджер')

    # исключаем из проверки тех, кто уже является менеджером этого кафе
    if venue:
        ids_set = set(manager_ids) - set(
            (
                await session.scalars(
                    select(User.id).where(User.venue_id == venue.id),
                )
            ).all(),
        )
    else:
        ids_set = set(manager_ids)
    select_statement = select(User.id).where(User.id.in_(ids_set))

    # Проверка существования пользователей
    existing_users = set((await session.scalars(select_statement)).all())
    missing_users = ids_set - existing_users
    if missing_users:
        raise ValueError(f'Пользователи с id {missing_users} не существуют')

    possible_managers = set(
        (
            await session.scalars(
                select_statement.where(
                    User.role != 'USER',
                ),
            )
        ).all(),
    )
    common_users = ids_set - possible_managers
    if common_users:
        raise ValueError(f'Пользователи с id {common_users} не являются менеджерами')

    active_managers = set(
        (
            await session.scalars(
                select(User.id).where(
                    User.id.in_(possible_managers),
                    User.is_active.is_(True),
                ),
            )
        ).all(),
    )
    inactive_managers = ids_set - active_managers
    if inactive_managers:
        raise ValueError(f'Пользователи с id {inactive_managers} деактивированы')

    # Проверка уже привязанных менеджеров
    existing_managers = set(
        (
            await session.scalars(
                select(User.id).where(
                    User.id.in_(active_managers),
                    User.venue_id.is_not(None),
                ),
            )
        ).all(),
    )

    if existing_managers:
        raise ValueError(
            f'Пользователи {existing_managers} уже привязаны к кафе',
        )


async def validate_existed_venue(venue_id: int, session: SessionDep) -> Venue:
    """Проверяет существование кафе по ID."""
    venue = await venue_crud.get(venue_id=venue_id, session=session)
    if venue is None:
        log(logging.INFO, f'Кафе с id={venue_id} не найдено')
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Кафе с таким id не найдено.',
        )
    return venue


async def validate_venue_ids(venue_ids: list[int] | None, session: SessionDep) -> None:
    """Проверяет по id существование кафе из списка."""
    if not venue_ids:
        return
    existed_venue_ids = set(
        await session.scalars(
            select(Venue.id).where(Venue.id.in_(venue_ids)),
        ),
    )
    missing_venue_ids = existed_venue_ids - set(venue_ids)
    if missing_venue_ids:
        log(logging.INFO, f'Кафе с id={missing_venue_ids} не существует')
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Одно или несколько из указанных кафе не найдены',
        )


def validate_current_admin(current_user: CurrentUserDep) -> User:
    """Проверяет доступ - только для администраторов."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Доступ только для администраторов',
        )
    return current_user


def validate_current_manager_or_admin(current_user: CurrentUserDep) -> User:
    """Проверяет доступ - для менеджеров и администраторов."""
    if current_user.role == UserRole.USER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Доступ только для менеджеров и администраторов',
        )
    return current_user


def validate_file(file: UploadFile) -> UploadFile:
    """Валидирует формат и размер изображения."""
    log(logging.DEBUG, f'Валидация файла "{file.filename}"...')

    log(logging.DEBUG, 'Проверяем размер файла...')
    file_size = getattr(file, 'size', None)
    if file_size is not None and file_size > MAX_MEDIA_SIZE:
        log(logging.WARNING, f'Размер файла {file_size} превышает допустимый {MAX_MEDIA_SIZE}')
        raise ValueError(INVALID_IMAGE_SIZE)

    log(logging.DEBUG, 'Проверяем расширение файла...')
    sufix = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if file.content_type not in ALLOWED_MEDIA_CONTENT_TYPES or sufix not in ALLOWED_MEDIA_EXTENSIONS:
        log(logging.WARNING, f'Недопустимые расширение({sufix}) или content_type({file.content_type}) файла')
        raise ValueError(INVALID_IMAGE_FORMAT)

    log(logging.DEBUG, 'Проверяем формат и целостность изображения с помощью Pillow...')
    try:
        image = Image.open(file.file)

        if image.format not in ALLOWED_FORMATS:
            log(logging.WARNING, f'Недопустимый формат изображения: {image.format}')
            raise ValueError('Недопустимый формат изображения')

        image.verify()  # проверка целостности файла
    except UnidentifiedImageError:
        log(logging.WARNING, 'Файл не является изображением')
        raise ValueError('Файл не является изображением')
    finally:
        file.file.seek(0)  # вернуть указатель в начало

    log(logging.DEBUG, f'Файл "{file.filename}" прошёл валидацию.')
    return file


async def validate_duplicate_slot(
    venue_id: int,
    start_time: time,
    end_time: time,
    session: AsyncSession,
    exclude_id: int | None = None,
) -> None:
    """Проверяет пересечение временного слота с существующими."""
    stmt = (
        select(TimeSlot)
        .where(TimeSlot.venue_id == venue_id)
        .where(TimeSlot.is_active.is_(True))
        .where(TimeSlot.start_time < end_time)
        .where(TimeSlot.end_time > start_time)
    )
    if exclude_id is not None:
        stmt = stmt.where(TimeSlot.id != exclude_id)
    result = await session.execute(stmt)
    existing = result.scalars().first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='Временный слот пересекается с существующим.',
        )


def validate_time_slot(
    start_time: time,
    end_time: time,
) -> None:
    """Валидирует время начала слота."""
    if start_time >= end_time:
        raise ValueError(
            f'Время начала бронирования '
            f'{start_time.strftime(SLOT_TIME_FORMAT)} '
            f'должно быть раньше окончания '
            f'{end_time.strftime(SLOT_TIME_FORMAT)}!',
        )
