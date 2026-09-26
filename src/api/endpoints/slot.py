import logging
from typing import Sequence

from fastapi import APIRouter, HTTPException, status

from core.constants import UserRole
from core.dependencies import CurrentUserDep, SessionDep
from core.logging import log
from core.validators import (
    validate_current_manager_or_admin,
    validate_duplicate_slot,
    validate_existed_venue,
)
from crud.slot import slot_crud
from models.slot import TimeSlot
from schemas.slot import TimeSlotCreate, TimeSlotInfo, TimeSlotUpdate

router = APIRouter(prefix='/venues/{venue_id}/time_slots')


@router.get(
    '/',
    response_model=list[TimeSlotInfo],
    summary='List of time slots in the venue',
    description=(
        'Get a list of time slots available for booking '
        'in the venue.\n\n'
        'For administrators and managers - '
        'all slots (with the option to select), '
        'for users - active slots only.'
    ),
)
async def get_time_slots_list(
    venue_id: int,
    session: SessionDep,
    user: CurrentUserDep,
    show_active: bool | None = True,
) -> Sequence[TimeSlotInfo]:
    """Return a list of the venue's time slots."""
    venue = await validate_existed_venue(venue_id, session)
    if user.role == UserRole.USER:
        return await slot_crud.get_all(
            session=session,
            venue_id=venue.id,
            is_active=True,  # active slots only for users
        )

    return await slot_crud.get_all(
        session=session,
        venue_id=venue.id,
        is_active=show_active,
    )


@router.get(
    '/{slot_id}',
    response_model=TimeSlotInfo,
    summary='Information about a time slot in the venue by its ID',
    description=(
        'Get information about a time slot in the venue by its ID.\n\n'
        'For administrators and managers - all slots, '
        'for users - active slots only.'
    ),
)
async def get_time_slot_by_id(
    venue_id: int,
    session: SessionDep,
    user: CurrentUserDep,
    slot_id: int,
) -> TimeSlotInfo:
    """Return information about a time slot by its ID."""
    log(logging.INFO, f'Request to get time slot id={slot_id}', actor=user)
    venue = await validate_existed_venue(venue_id, session)
    slot: TimeSlot | None = await slot_crud.get(slot_id, session)
    if not slot or user.role == UserRole.USER and not slot.is_active:
        message = f'Time slot {slot_id} not found.'
        log(logging.INFO, message)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Time slot not found.',
        )
    if not slot.venue.id == venue.id:
        message = f'Time slot {slot_id} does not belong to venue {venue_id}.'
        log(logging.INFO, message)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='This venue does not have this booking slot.',
        )
    return slot


@router.post(
    '/',
    response_model=TimeSlotInfo,
    status_code=status.HTTP_201_CREATED,
    summary='New time slot in the venue',
    description=('Creates a new time slot in the venue.\n\nOnly for administrators and managers.'),
)
async def create_time_slot(
    venue_id: int,
    slot_in: TimeSlotCreate,
    session: SessionDep,
    user: CurrentUserDep,
) -> TimeSlotInfo:
    """Create a new time slot in the venue."""
    log(logging.INFO, f'Request to create a time slot for Venue[id={venue_id}]', actor=user)
    validate_current_manager_or_admin(user)
    venue = await validate_existed_venue(venue_id, session)
    await validate_duplicate_slot(
        venue_id=venue.id,
        start_time=slot_in.start_time,
        end_time=slot_in.end_time,
        session=session,
    )
    slot_data = slot_in.model_dump()
    slot_data['venue_id'] = venue.id
    new_slot = await slot_crud.create(
        obj_in=slot_data,
        session=session,
    )
    await session.commit()
    await session.refresh(new_slot, attribute_names=['venue'])

    return new_slot


@router.patch(
    '/{slot_id}',
    response_model=TimeSlotInfo,
    summary='Update time slot information in the venue by its ID',
    description=(
        'Update information about a time slot in the venue by its ID.\n\n'
        'Only for administrators and managers.'
    ),
)
async def update_time_slot(
    venue_id: int,
    slot_id: int,
    slot_in: TimeSlotUpdate,
    session: SessionDep,
    user: CurrentUserDep,
) -> TimeSlotInfo:
    """Update time slot data by its ID."""
    log(logging.INFO, f'Request to update TimeSlot[id={slot_id}]', actor=user)
    validate_current_manager_or_admin(user)
    venue = await validate_existed_venue(venue_id, session)
    slot = await slot_crud.get_one_or_none(
        session=session,
        id=slot_id,
        venue_id=venue.id,
    )
    if not slot:
        message = f'Time slot {slot_id} not found or does not belong to venue {venue.id}.'
        log(logging.INFO, message)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Time slot not found.',
        )

    if 'start_time' in slot_in.model_dump() or 'end_time' in slot_in.model_dump():
        start = slot_in.start_time if slot_in.start_time is not None else slot.start_time
        end = slot_in.end_time if slot_in.end_time is not None else slot.end_time
        await validate_duplicate_slot(
            venue_id=venue.id,
            start_time=start,
            end_time=end,
            session=session,
            exclude_id=slot.id,
        )
    updated_slot = await slot_crud.update(
        session=session,
        db_obj=slot,
        obj_in=slot_in,
    )
    await session.commit()

    return updated_slot
