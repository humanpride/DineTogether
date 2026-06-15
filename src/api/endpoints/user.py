import logging
from typing import Sequence

from fastapi import APIRouter, HTTPException, Query, status

from core.constants import UserRole
from core.dependencies import CurrentUserDep, SessionDep
from core.logging import log
from core.validators import (
    validate_current_admin,
    validate_current_manager_or_admin,
    validate_unique_email,
    validate_unique_phone,
    validate_unique_username,
)
from crud.user import user_crud
from schemas.user import (
    UserCreate,
    UserDeactivate,
    UserInfo,
    UserShortInfo,
    UserUpdate,
    UserUpdateMe,
)

router = APIRouter(prefix='/users')


@router.get(
    '/me',
    response_model=UserShortInfo,
)
async def get_user_me(
    current_user: CurrentUserDep,
) -> UserShortInfo:
    """Получение данных о текущем пользователе."""
    return current_user


@router.patch(
    '/me',
    response_model=UserShortInfo,
)
async def patch_user_me(
    current_user: CurrentUserDep,
    user_data: UserUpdateMe,
    session: SessionDep,
) -> UserShortInfo:
    """Обновление данных о текущем пользователе."""
    # Проверка уникальности каждого поля отдельно
    if user_data.username:
        await validate_unique_username(
            session=session,
            username=user_data.username,
            current_username=current_user.username,
            user_id=current_user.id,
        )

    if user_data.email:
        await validate_unique_email(
            session=session,
            email=user_data.email,
            current_email=current_user.email,
            user_id=current_user.id,
        )

    if user_data.phone:
        await validate_unique_phone(
            session=session,
            phone=user_data.phone,
            current_phone=current_user.phone,
            user_id=current_user.id,
        )

    updated_user = await user_crud.update(
        db_obj=current_user,
        obj_in=user_data,
        session=session,
    )
    await session.commit()

    return updated_user


@router.get(
    '/',
    response_model=list[UserShortInfo],
)
async def get_users(
    session: SessionDep,
    user: CurrentUserDep,
    show_active: bool | None = Query(
        default=None,
        description='Выводить пользователей по аргументу is_active',
    ),
) -> Sequence[UserShortInfo]:
    """Возвращает данные о всех пользователях.

    show_active:
        Фильтр по признаку активности пользователя

    - True - показывать только активных
    - False - показывать только неактивных
    - None - показывать всех

    Доступ: `ADMIN`/`MANAGER`

    """
    validate_current_manager_or_admin(user)
    return await user_crud.get_all(session=session, is_active=show_active)


@router.post(
    '/',
    response_model=UserInfo,
    status_code=status.HTTP_201_CREATED,
)
async def register_user_by_admin_or_manager(
    user: CurrentUserDep,
    user_data: UserCreate,
    session: SessionDep,
) -> UserInfo:
    """Регистрация нового пользователя."""
    current_user = validate_current_manager_or_admin(user)
    # Проверка для MANAGER: может создавать только USER
    if current_user.role == UserRole.MANAGER and user_data.role != UserRole.USER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Менеджер может создавать только пользователей.',
        )

    await validate_unique_username(
        session=session,
        username=user_data.username,
        current_username=None,
        user_id=None,
    )

    if user_data.email:
        await validate_unique_email(
            session=session,
            email=user_data.email,
            current_email=None,
            user_id=None,
        )

    if user_data.phone:
        await validate_unique_phone(
            session=session,
            phone=user_data.phone,
            current_phone=None,
            user_id=None,
        )

    # проверка на наличие хотя бы одного контактного поля (email или телефон)
    if not user_data.email and not user_data.phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Должен быть указан email или телефон',
        )

    new_user = await user_crud.create_user(
        obj_in=UserCreate(
            username=user_data.username,
            email=user_data.email,
            phone=user_data.phone,
            password=user_data.password,
            role=user_data.role,
            is_active=user_data.is_active,
        ),
        session=session,
    )
    await session.commit()

    return new_user


@router.get(
    '/{user_id}',
)
async def get_user_by_id(
    user_id: int,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> UserInfo | UserShortInfo:
    """Получение пользователя по id."""
    validate_current_manager_or_admin(current_user)
    user = await user_crud.get(obj_id=user_id, session=session)

    if not user:
        log(logging.INFO, f'Пользователь с id={user_id} не найден', actor=current_user)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Пользователь не найден',
        )

    if current_user.role == UserRole.ADMIN:
        return UserInfo.model_validate(user)
    return UserShortInfo.model_validate(user)


@router.patch(
    '/{user_id}',
    response_model=UserInfo,
)
async def update_user_by_id(
    user_id: int,
    user_data: UserUpdate,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> UserInfo:
    """Обновление пользователя по id.

    Доступ: `ADMIN`/`MANAGER`
    """
    validate_current_manager_or_admin(current_user)
    user_to_update = await user_crud.get(obj_id=user_id, session=session)

    if not user_to_update:
        log(logging.INFO, f'Пользователь с id={user_id} не найден', actor=current_user)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Пользователь не найден',
        )

    # ограничения для менеджера
    if current_user.role == UserRole.MANAGER and (
        user_to_update.role != UserRole.USER or any([user_data.role, user_data.is_active])
    ):
        log(
            logging.INFO,
            f'У пользователя {current_user.username} недостаточно прав для изменения '
            f'пользователя {user_to_update.username} с данными: {user_data.model_dump()}',
            actor=current_user,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Недостаточно прав для изменения этих данных',
        )

    # Проверка: запрещаем смену роли у другого администратора
    if user_data.role is not None and user_to_update.role == UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Нельзя изменить роль администратора',
        )

    # Проверка: нельзя деактивировать самого себя
    if user_data.is_active is False and user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Нельзя деактивировать самого себя',
        )

    if user_data.username:
        await validate_unique_username(
            session=session,
            username=user_data.username,
            current_username=user_to_update.username,
            user_id=user_id,
        )

    if user_data.email:
        await validate_unique_email(
            session=session,
            email=user_data.email,
            current_email=user_to_update.email,
            user_id=user_id,
        )

    if user_data.phone:
        await validate_unique_phone(
            session=session,
            phone=user_data.phone,
            current_phone=user_to_update.phone,
            user_id=user_id,
        )

    updated_user = user_crud.update(
        db_obj=user_to_update,
        obj_in=user_data,
        session=session,
    )
    await session.commit()

    return await updated_user


@router.patch(
    '/{user_id}/deactivate',
    response_model=UserInfo,
)
async def deactivate_user_by_id(
    user_id: int,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> UserInfo:
    """Деактивирует пользователя. Только для ADMIN."""
    validate_current_admin(current_user)
    # Нельзя деактивировать себя
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Нельзя деактивировать самого себя',
        )

    # Получаем пользователя для деактивации
    user_to_deactivate = await user_crud.get(obj_id=user_id, session=session)

    if not user_to_deactivate:
        log(logging.INFO, f'Пользователь с id={user_id} не найден', actor=current_user)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Пользователь не найден',
        )

    # Если уже деактивирован
    if not user_to_deactivate.is_active:
        log(logging.INFO, f'Пользователь с id={user_id} уже деактивирован', actor=current_user)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Пользователь уже деактивирован',
        )

    updated_user = await user_crud.update(
        db_obj=user_to_deactivate,
        obj_in=UserDeactivate(is_active=False),
        session=session,
    )
    await session.commit()

    return updated_user


@router.patch(
    '/{user_id}/activate',
    response_model=UserInfo,
)
async def activate_user_by_id(
    user_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> UserInfo:
    """Активирует пользователя. Только для ADMIN."""
    validate_current_admin(current_user)
    user_to_activate = await user_crud.get(obj_id=user_id, session=session)

    if not user_to_activate:
        log(logging.INFO, f'Пользователь с id={user_id} не найден', actor=current_user)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Пользователь не найден',
        )

    # Если уже активирован
    if user_to_activate.is_active:
        log(logging.INFO, f'Пользователь с id={user_id} уже активирован', actor=current_user)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Пользователь уже активирован',
        )

    updated_user = await user_crud.update(
        db_obj=user_to_activate,
        obj_in=UserDeactivate(is_active=True),
        session=session,
    )
    await session.commit()

    return updated_user
