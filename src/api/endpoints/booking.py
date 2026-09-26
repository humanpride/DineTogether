import logging
from typing import Sequence

from fastapi import APIRouter, HTTPException, status

from core.dependencies import CurrentUserDep, SessionDep
from core.logging import log
from crud.booking import booking_crud
from schemas.booking import BookingCreate, BookingInfo, BookingUpdate
from services.booking.service import booking_service

router = APIRouter(prefix='/booking')


@router.get(
    '/',
    response_model=list[BookingInfo],
    response_model_exclude_none=True,
)
async def get_all_bookings(
    session: SessionDep,
    show_active: bool | None = True,
    venue_id: int | None = None,
    user_id: int | None = None,
) -> Sequence[BookingInfo]:
    """Return a list of bookings with available filters."""
    return await booking_crud.get_all(
        session=session,
        is_active=show_active,
        venue_id=venue_id,
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
    """Create a new booking."""
    try:
        return await booking_service.create_booking(booking_in, user.id, session)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        )


@router.get(
    '/{booking_id}',
    response_model=BookingInfo,
    response_model_exclude_none=True,
)
async def get_booking(booking_id: int, session: SessionDep) -> BookingInfo:
    """Return a booking by its ID."""
    booking = await booking_crud.get(booking_id=booking_id, session=session)
    if not booking:
        message = f'Booking with id={booking_id} not found'
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
    """Update a booking by its ID."""
    booking = await booking_crud.get(booking_id=booking_id, session=session)
    if booking is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Booking not found.',
        )
    try:
        return await booking_service.update_booking(booking, booking_in, session)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        )
