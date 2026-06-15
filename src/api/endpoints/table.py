import logging
from typing import Sequence

from fastapi import APIRouter, HTTPException, status

from core.constants import UserRole
from core.dependencies import CurrentUserDep, SessionDep
from core.logging import log
from core.validators import (
    validate_current_manager_or_admin,
    validate_existed_cafe,
)
from crud.table import table_crud
from schemas.table import TableCreate, TableInfo, TableUpdate

router = APIRouter(prefix='/cafes/{cafe_id}/tables')


@router.get(
    '/',
    response_model=list[TableInfo],
    response_model_exclude_none=True,
)
async def get_all_tables(
    cafe_id: int,
    session: SessionDep,
    user: CurrentUserDep,
    show_active: bool | None = None,
) -> Sequence[TableInfo]:
    """Возвращает список столов в кафе.

    По умолчанию показывает:
    - для пользователя - только активные столы в кафе (всегда, вне зависимости от значения параметра)
    - для администратора - все столы в кафе (и активные и не активные)
    - для менеджера - активные столы в кафе

    show_active:
    - True - Только активные столы
    - False - Только неактивные столы
    - None - Все столы в кафе
    """
    cafe = await validate_existed_cafe(cafe_id, session)
    if user.role == UserRole.USER:
        show_active = True
    return await table_crud.get_all(
        session=session,
        cafe_id=cafe.id,
        is_active=show_active,
    )


@router.post(
    '/',
    response_model=TableInfo,
    status_code=status.HTTP_201_CREATED,
)
async def create_new_table(
    cafe_id: int,
    table_in: TableCreate,
    session: SessionDep,
    user: CurrentUserDep,
) -> TableInfo:
    """Создает новый стол в кафе.

    Только для администраторов и менеджеров.
    """
    validate_current_manager_or_admin(user)
    cafe = await validate_existed_cafe(cafe_id, session)
    table_data = table_in.model_dump()
    table_data['cafe_id'] = cafe.id
    new_table = await table_crud.create(
        obj_in=table_data,
        session=session,
    )
    await session.commit()
    await session.refresh(new_table, attribute_names=['cafe'])

    return new_table


@router.get(
    '/{table_id}',
    response_model=TableInfo,
)
async def get_table(
    cafe_id: int,
    table_id: int,
    session: SessionDep,
    user: CurrentUserDep,
    show_active: bool | None = None,
) -> TableInfo:
    """Получение информации о столе в кафе по его ID.

    Для администраторов и менеджеров - все столы, для пользователей - только активные.

    show_active:
    - True - Только активные столы
    - False - Только неактивные столы
    - None - Все столы в кафе (и активные и не активные)
    """
    cafe = await validate_existed_cafe(cafe_id, session)

    if user.role == UserRole.USER:
        show_active = True

    table = await table_crud.get_one_or_none(
        session=session,
        id=table_id,
        cafe_id=cafe.id,
        is_active=show_active,
    )

    if table is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Стол не найден',
        )
    return table


@router.patch(
    '/{table_id}',
    response_model=TableInfo,
)
async def update_table(
    cafe_id: int,
    table_id: int,
    table_in: TableUpdate,
    session: SessionDep,
    user: CurrentUserDep,
) -> TableInfo:
    """Обновление информации о столе в кафе по его ID.

    Доступ: `ADMIN`/`MANAGER`
    """
    validate_current_manager_or_admin(user)
    cafe = await validate_existed_cafe(cafe_id, session)
    table = await table_crud.get_one_or_none(
        session=session,
        id=table_id,
        cafe_id=cafe.id,
    )
    if table is None:
        log(logging.INFO, f'Стол с id={table_id} не найден или не принадлежит кафе {cafe.id}', actor=user)
        raise HTTPException(
            status_code=404,
            detail='Стол не найден',
        )
    updated_table = await table_crud.update(
        db_obj=table,
        obj_in=table_in,
        session=session,
    )
    await session.commit()

    return updated_table
