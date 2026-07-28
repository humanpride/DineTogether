import logging
from typing import Sequence

from fastapi import APIRouter, HTTPException, status

from core.constants import UserRole
from core.dependencies import CurrentUserDep, SessionDep
from core.logging import log
from core.validators import (
    validate_current_manager_or_admin,
    validate_existed_venue,
    validate_venue_managers,
)
from crud.venue import venue_crud
from schemas.venue import VenueCreate, VenueInfo, VenueUpdate

router = APIRouter(prefix='/venues')


@router.get(
    '/',
    response_model=list[VenueInfo],
    response_model_exclude_none=True,
)
async def get_all_venue(
    session: SessionDep,
    user: CurrentUserDep,
    show_active: bool | None = None,
) -> Sequence[VenueInfo]:
    """Получение списка кафе.

    - для администраторов и менеджеров - все кафе
    - для пользователей - только активные.

    show_active:
        True -> Только активные кафе.
        False -> Только неактивные кафе.
        None -> Все кафе (и активные и не активные).
    """
    if user.role == UserRole.USER:
        show_active = True
    return await venue_crud.get_all(is_active=show_active, session=session)


@router.post(
    '/',
    response_model=VenueInfo,
    status_code=status.HTTP_201_CREATED,
)
async def create_venue(
    venue_in: VenueCreate,
    session: SessionDep,
    user: CurrentUserDep,
) -> VenueInfo:
    """Создает новое кафе.

    Только для администраторов и менеджеров.
    """
    current_user = validate_current_manager_or_admin(user)
    try:
        await validate_venue_managers(
            manager_ids=venue_in.manager_ids,
            session=session,
        )
    except ValueError as error:
        log(logging.INFO, str(error), current_user)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail='Некорректный список менеджеров',
        )
    try:
        venue = await venue_crud.create(obj_in=venue_in, session=session)
        await session.commit()
        return venue
    except Exception as error:
        log(logging.ERROR, str(error), current_user)
        await session.rollback()
        log(logging.ERROR, str(error), None)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail='Некорректные данные кафе',
        ) from error


@router.get(
    '/{venue_id}',
    response_model=VenueInfo,
)
async def get_venue(
    venue_id: int,
    session: SessionDep,
    user: CurrentUserDep,
    show_active: bool | None = None,
) -> VenueInfo:
    """Получение информации о кафе по его ID.

    - для администраторов и менеджеров - загружается любое кафе
    - для пользователей - только активные, иначе 404

    show_active:
        True -> Только активные кафе
        False -> Только неактивные кафе
        None -> Все кафе
    """
    venue = await venue_crud.get(venue_id, session)
    if (
        not venue
        or (show_active is not None and venue.is_active != show_active)
        or (user.role == UserRole.USER and not venue.is_active)
    ):
        log(logging.INFO, f'Venue[id={venue_id}, is_active={show_active}] не найдено', actor=user)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Кафе не найдено.',
        )
    return venue


@router.patch(
    '/{venue_id}',
    response_model=VenueInfo,
)
async def update_venue(
    venue_id: int,
    venue_in: VenueUpdate,
    session: SessionDep,
    user: CurrentUserDep,
) -> VenueInfo:
    """Обновление информации о кафе по его ID.

    Только для администраторов и менеджеров.
    """
    validate_current_manager_or_admin(user)
    venue = await validate_existed_venue(venue_id, session)
    if venue_in.manager_ids is not None:
        try:
            await validate_venue_managers(
                manager_ids=venue_in.manager_ids,
                session=session,
                venue=venue,
            )
        except ValueError as error:
            log(logging.INFO, str(error), user)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail='Некорректный список менеджеров',
            )
    updated_venue = await venue_crud.update(db_obj=venue, obj_in=venue_in, session=session)
    await session.commit()

    return updated_venue
