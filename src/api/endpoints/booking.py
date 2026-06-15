import logging
from typing import Sequence

from fastapi import APIRouter, HTTPException, status

from core.dependencies import CurrentUserDep, SessionDep
from core.logging import log
from core.validators import (
    validate_booking_conflicts,
    validate_booking_date,
    validate_booking_references,
    validate_existed_cafe,
)
from crud.booking import booking_crud
from schemas.booking import BookingCreate, BookingInfo, BookingUpdate
from services.booking_service import handle_booking_created

router = APIRouter(prefix='/booking')


@router.get(
    '/',
    response_model=list[BookingInfo],
    response_model_exclude_none=True,
)
async def get_all_bookings(
    session: SessionDep,
    show_active: bool | None = True,
    cafe_id: int | None = None,
    user_id: int | None = None,
) -> Sequence[BookingInfo]:
    """Возвращает список бронирований с доступными фильтрами."""
    return await booking_crud.get_all(
        session=session,
        is_active=show_active,
        cafe_id=cafe_id,
        user_id=user_id,
    )


@router.post(
    '/',
    response_model=BookingInfo,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
)
async def create_booking(
    booking_in: BookingCreate,
    session: SessionDep,
    user: CurrentUserDep,
) -> BookingInfo:
    """Создает новое бронирование."""
    try:
        await validate_existed_cafe(booking_in.cafe_id, session)
        await validate_booking_references(
            booking_in=booking_in,
            session=session,
            cafe_id=booking_in.cafe_id,
        )
        await validate_booking_conflicts(
            booking_in=booking_in,
            session=session,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        )

    booking = await booking_crud.create(
        obj_in=booking_in,
        user_id=user.id,
        session=session,
    )
    await session.commit()
    await session.refresh(booking, attribute_names=['cafe', 'tables_slots', 'user'])
    await handle_booking_created(booking, session)

    return booking


@router.get(
    '/{booking_id}',
    response_model=BookingInfo,
    response_model_exclude_none=True,
)
async def get_booking(booking_id: int, session: SessionDep) -> BookingInfo:
    """Возвращает бронирование по ID."""
    booking = await booking_crud.get(booking_id=booking_id, session=session)
    if not booking:
        message = f'Бронирование с id={booking_id} не найдено'
        log(logging.WARNING, message)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message,
        )
    return BookingInfo.model_validate(booking)


@router.patch(
    '/{booking_id}',
    response_model=BookingInfo,
    response_model_exclude_none=True,
)
async def update_booking(
    booking_id: int,
    booking_in: BookingUpdate,
    user: CurrentUserDep,
    session: SessionDep,
) -> BookingInfo:
    """Обновляет бронирование по ID."""
    booking = await booking_crud.get(booking_id=booking_id, session=session)
    if booking is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Бронирование не найдено.',
        )
    try:
        await validate_booking_references(
            booking_in=booking_in,
            session=session,
            cafe_id=booking.cafe_id,
        )
        await validate_booking_conflicts(
            booking_in=booking_in,
            session=session,
            booking_id=booking.id,
        )
        await validate_booking_date(booking_date=booking_in.booking_date or booking.booking_date)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        )
    try:
        await booking_crud.update(
            booking=booking,
            obj_in=booking_in,
            user=user,
            session=session,
        )
        await handle_booking_created(booking, session)
        return booking
    except Exception as error:
        log(
            logging.ERROR,
            f'Ошибка при обновлении бронирования {booking_id}: {error}',
            actor=user,
        )
        raise
