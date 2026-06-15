import logging
from typing import Sequence

from fastapi import APIRouter, HTTPException, status

from core.constants import UserRole
from core.dependencies import CurrentUserDep, SessionDep
from core.logging import log
from core.validators import (
    validate_current_manager_or_admin,
    validate_duplicate_slot,
    validate_existed_cafe,
)
from crud.slot import slot_crud
from models.slot import TimeSlot
from schemas.slot import TimeSlotCreate, TimeSlotInfo, TimeSlotUpdate

router = APIRouter(prefix='/cafes/{cafe_id}/time_slots')


@router.get(
    '/',
    response_model=list[TimeSlotInfo],
    summary='Список временных слотов в кафе',
    description=(
        'Получение списка доступных для бронирования '
        'временных слотов в кафе. '
        'Для администраторов и менеджеров - '
        'все слоты (с возможностью выбора), '
        'для пользователей - только активные.'
    ),
)
async def get_time_slots_list(
    cafe_id: int,
    session: SessionDep,
    user: CurrentUserDep,
    show_active: bool | None = True,
) -> Sequence[TimeSlotInfo]:
    """Возвращает список временных слотов кафе."""
    cafe = await validate_existed_cafe(cafe_id, session)
    if user.role == UserRole.USER:
        return await slot_crud.get_all(
            session=session,
            cafe_id=cafe.id,
            is_active=True,  # для юзеров всегда только активные
        )

    return await slot_crud.get_all(
        session=session,
        cafe_id=cafe.id,
        is_active=show_active,
    )


@router.get(
    '/{slot_id}',
    response_model=TimeSlotInfo,
    summary='Информация о временном слоте в кафе по его ID',
    description=(
        'Получение информации о временном слоте в кафе по его ID. '
        'Для администраторов и менеджеров - все слоты, '
        'для пользователей - только активные.'
    ),
)
async def get_time_slot_by_id(
    cafe_id: int,
    session: SessionDep,
    user: CurrentUserDep,
    slot_id: int,
) -> TimeSlotInfo:
    """Возвращает информацию о временном слоте по его ID."""
    log(logging.INFO, f'Запрос на получение временного слота id={slot_id}', actor=user)
    cafe = await validate_existed_cafe(cafe_id, session)
    slot: TimeSlot | None = await slot_crud.get(slot_id, session)
    if not slot or user.role == UserRole.USER and not slot.is_active:
        message = f'Временный слот {slot_id} не найден.'
        log(logging.INFO, message)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Временный слот не найден.',
        )
    if not slot.cafe.id == cafe.id:
        message = f'Временный слот {slot_id} не принадлежит кафе {cafe_id}.'
        log(logging.INFO, message)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='У данного кафе нет такого слота бронирования.',
        )
    return slot


@router.post(
    '/',
    response_model=TimeSlotInfo,
    status_code=status.HTTP_201_CREATED,
    summary='Новый временной слот в кафе',
    description=('Создаёт новый временный слот в кафе. Только для администраторов и менеджеров.'),
)
async def create_time_slot(
    cafe_id: int,
    slot_in: TimeSlotCreate,
    session: SessionDep,
    user: CurrentUserDep,
) -> TimeSlotInfo:
    """Создаёт новый временный слот в кафе."""
    log(logging.INFO, f'Запрос на создание временного слота для Cafe[id={cafe_id}]', actor=user)
    validate_current_manager_or_admin(user)
    cafe = await validate_existed_cafe(cafe_id, session)
    await validate_duplicate_slot(
        cafe_id=cafe.id,
        start_time=slot_in.start_time,
        end_time=slot_in.end_time,
        session=session,
    )
    slot_data = slot_in.model_dump()
    slot_data['cafe_id'] = cafe.id
    new_slot = await slot_crud.create(
        obj_in=slot_data,
        session=session,
    )
    await session.commit()
    await session.refresh(new_slot, attribute_names=['cafe'])

    return new_slot


@router.patch(
    '/{slot_id}',
    response_model=TimeSlotInfo,
    summary='Обновление информации о временном слоте в кафе по его ID',
    description=(
        'Обновление информации о временом слоте в кафе по его ID. Только для администраторов и менеджеров.'
    ),
)
async def update_time_slot(
    cafe_id: int,
    slot_id: int,
    slot_in: TimeSlotUpdate,
    session: SessionDep,
    user: CurrentUserDep,
) -> TimeSlotInfo:
    """Обновляет данные временного слота по его ID."""
    log(logging.INFO, f'Запрос на обновление TimeSlot[id={slot_id}]', actor=user)
    validate_current_manager_or_admin(user)
    cafe = await validate_existed_cafe(cafe_id, session)
    slot = await slot_crud.get_one_or_none(
        session=session,
        id=slot_id,
        cafe_id=cafe.id,
    )
    if not slot:
        message = f'Временный слот {slot_id} не найден или не принадлежит кафе {cafe.id}.'
        log(logging.INFO, message)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Временный слот не найден.',
        )

    if 'start_time' in slot_in.model_dump() or 'end_time' in slot_in.model_dump():
        start = slot_in.start_time if slot_in.start_time is not None else slot.start_time
        end = slot_in.end_time if slot_in.end_time is not None else slot.end_time
        await validate_duplicate_slot(
            cafe_id=cafe.id,
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
