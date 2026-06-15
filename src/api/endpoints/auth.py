import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from core.constants import UserRole
from core.dependencies import CurrentUserDep, SessionDep
from core.logging import log
from core.security import (
    create_access_token,
    get_password_hash,
    verify_password,
)
from core.validators import (
    validate_unique_email,
    validate_unique_phone,
    validate_unique_username,
)
from crud.user import user_crud
from schemas.token import Token
from schemas.user import (
    UserChangePassword,
    UserCreate,
    UserLogin,
    UserRegister,
    UserShortInfo,
    UserUpdateDBPassword,
    login_field_data,
)

router = APIRouter(prefix='/auth')


@router.post('/register', response_model=UserShortInfo, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserRegister,
    session: SessionDep,
) -> UserShortInfo:
    """Регистрация нового пользователя."""
    # Проверка уникальности каждого поля отдельно
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
        UserCreate(
            username=user_data.username,
            email=user_data.email,
            phone=user_data.phone,
            telegram_id=user_data.telegram_id,
            password=user_data.password,
            role=UserRole.USER,
            is_active=True,
        ),
        session=session,
    )
    await session.commit()

    return new_user


@router.post('/login', response_model=Token, status_code=status.HTTP_200_OK)
async def auth_user(
    user_data: UserLogin,
    session: SessionDep,
) -> Token:
    """Аутентификация пользователя."""
    # Поиск пользователя по email или телефону
    try:
        login = await login_field_data(user_data.login)
    except ValueError as error:
        log(logging.WARNING, f'Ошибка валидации логина: {error}')
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail='Неверный email/телефон',
        )
    user = await user_crud.get_one_or_none(session, **login)

    # Проверка существования пользователя и совпадения пароля
    if not user or not verify_password(user_data.password, user.hashed_password):
        log(logging.WARNING, f'Неудачная попытка входа для логина: {user_data.login}')
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail='Неверный email/телефон или пароль',
            headers={'WWW-Authenticate': 'Bearer'},
        )

    if not user.is_active:
        log(logging.WARNING, f'Попытка входа в деактивированный аккаунт: {user_data.login}')
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Аккаунт деактивирован',
        )

    # Создание JWT токенов
    token_data = {'sub': str(user.id), 'role': user.role.value}
    access_token = create_access_token(data=token_data)
    log(logging.INFO, f'Пользователь {user.username} успешно аутентифицирован')
    return Token(
        access_token=access_token,
        token_type='bearer',
    )


@router.post('/test-exception', status_code=status.HTTP_200_OK)
async def logout(
    current_user: CurrentUserDep,
) -> dict:
    """Тестирование вывода HTTPException."""
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail='Тестовая ошибка для проверки обработки исключений',
    )


@router.post('/token', response_model=Token, include_in_schema=False)
async def auth_user_form(
    session: SessionDep,
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Token:
    """Эндпоинт для OAuth2."""
    # Поиск пользователя по email или телефону
    try:
        login = await login_field_data(form_data.username)
    except ValueError as error:
        log(logging.WARNING, f'Ошибка валидации логина: {error}')
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail='Неверный email/телефон',
        )
    log(logging.DEBUG, f'Логин определён как {login}')
    log(logging.DEBUG, f'Поиск пользователя с данными: {login}')
    user = await user_crud.get_one_or_none(session, **login)
    if not user:
        log(logging.WARNING, f'Пользователь не найден для логина: {form_data.username}')
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail='Неверный email/телефон или пароль',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    log(logging.DEBUG, 'Пользователь найден, проверка пароля...')

    # Проверка корректности пароля
    if not verify_password(form_data.password, user.hashed_password):
        log(logging.WARNING, f'Неудачная попытка входа для логина: {form_data.username}')
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail='Неверный email/телефон или пароль',
            headers={'WWW-Authenticate': 'Bearer'},
        )

    # Создание JWT токенов
    token_data = {'sub': str(user.id), 'role': user.role.value}
    access_token = create_access_token(data=token_data)
    log(logging.INFO, f'Пользователь {user.username} успешно аутентифицирован')
    return Token(
        access_token=access_token,
        token_type='bearer',
    )


@router.post('/change-password', status_code=status.HTTP_200_OK)
async def change_password(
    password_data: UserChangePassword,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> dict:
    """Смена пароля пользователя."""
    # Проверяем старый пароль
    if not verify_password(password_data.old_password, current_user.hashed_password):
        log(
            logging.WARNING,
            'Введён неверный старый пароль',
            actor=current_user.username,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail='Неверный старый пароль',
        )

    # Проверяем, что новый пароль отличается от старого
    if verify_password(password_data.new_password, current_user.hashed_password):
        log(
            logging.WARNING,
            'Введён новый пароль, который совпадает со старым',
            actor=current_user.username,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail='Новый пароль должен отличаться от старого',
        )

    # Создаем объект для обновления
    user_update = UserUpdateDBPassword(
        hashed_password=get_password_hash(password_data.new_password),
    )

    await user_crud.update(
        db_obj=current_user,
        obj_in=user_update,
        session=session,
    )
    await session.commit()
    log(
        logging.INFO,
        'Пользователь успешно изменил пароль',
        actor=current_user.username,
    )
    return {
        'message': 'Пароль успешно изменен',
    }
