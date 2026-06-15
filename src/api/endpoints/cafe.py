import logging
from typing import Sequence

from fastapi import APIRouter, HTTPException, status

from core.constants import UserRole
from core.dependencies import CurrentUserDep, SessionDep
from core.logging import log
from core.validators import (
    validate_cafe_managers,
    validate_current_manager_or_admin,
    validate_existed_cafe,
)
from crud.cafe import cafe_crud
from schemas.cafe import CafeCreate, CafeInfo, CafeUpdate

router = APIRouter(prefix='/cafes')


@router.get(
    '/',
    response_model=list[CafeInfo],
    response_model_exclude_none=True,
)
async def get_all_cafe(
    session: SessionDep,
    user: CurrentUserDep,
    show_active: bool | None = None,
) -> Sequence[CafeInfo]:
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
    return await cafe_crud.get_all(is_active=show_active, session=session)


@router.post(
    '/',
    response_model=CafeInfo,
    status_code=status.HTTP_201_CREATED,
)
async def create_cafe(
    cafe_in: CafeCreate,
    session: SessionDep,
    user: CurrentUserDep,
) -> CafeInfo:
    """Создает новое кафе.

    Только для администраторов и менеджеров.
    """
    current_user = validate_current_manager_or_admin(user)
    try:
        await validate_cafe_managers(
            manager_ids=cafe_in.manager_ids,
            session=session,
        )
    except ValueError as error:
        log(logging.INFO, str(error), current_user)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail='Некорректный список менеджеров',
        )
    try:
        cafe = await cafe_crud.create(obj_in=cafe_in, session=session)
        await session.commit()
        return cafe
    except Exception as error:
        log(logging.ERROR, str(error), current_user)
        await session.rollback()
        log(logging.ERROR, str(error), None)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail='Некорректные данные кафе',
        ) from error


@router.get(
    '/{cafe_id}',
    response_model=CafeInfo,
)
async def get_cafe(
    cafe_id: int,
    session: SessionDep,
    user: CurrentUserDep,
    show_active: bool | None = None,
) -> CafeInfo:
    """Получение информации о кафе по его ID.

    - для администраторов и менеджеров - загружается любое кафе
    - для пользователей - только активные, иначе 404

    show_active:
        True -> Только активные кафе
        False -> Только неактивные кафе
        None -> Все кафе
    """
    cafe = await cafe_crud.get(cafe_id, session)
    if (
        not cafe
        or (show_active is not None and cafe.is_active != show_active)
        or (user.role == UserRole.USER and not cafe.is_active)
    ):
        log(logging.INFO, f'Cafe[id={cafe_id}, is_active={show_active}] не найдено', actor=user)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Кафе не найдено.',
        )
    return cafe


@router.patch(
    '/{cafe_id}',
    response_model=CafeInfo,
)
async def update_cafe(
    cafe_id: int,
    cafe_in: CafeUpdate,
    session: SessionDep,
    user: CurrentUserDep,
) -> CafeInfo:
    """Обновление информации о кафе по его ID.

    Только для администраторов и менеджеров.
    """
    validate_current_manager_or_admin(user)
    cafe = await validate_existed_cafe(cafe_id, session)
    if cafe_in.manager_ids is not None:
        try:
            await validate_cafe_managers(
                manager_ids=cafe_in.manager_ids,
                session=session,
                cafe=cafe,
            )
        except ValueError as error:
            log(logging.INFO, str(error), user)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail='Некорректный список менеджеров',
            )
    updated_cafe = await cafe_crud.update(db_obj=cafe, obj_in=cafe_in, session=session)
    await session.commit()

    return updated_cafe
