import logging
import traceback
from typing import Annotated, AsyncIterator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.logging import log
from core.security import decode_token
from core.settings import settings
from crud.user import user_crud
from models.user import User

async_engine = create_async_engine(
    url=settings.db_url,
    pool_pre_ping=True,
)

session_maker: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=async_engine,
    expire_on_commit=False,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Получение асинхронной сессии для FastAPI Depends."""
    session = session_maker()
    try:
        yield session
        await session.commit()
    except SQLAlchemyError as exc:
        await session.rollback()
        log(
            logging.ERROR,
            f'Ошибка БД: {exc}',
        )
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Ошибка при работе с БД',
        )
    finally:
        await session.close()


SessionDep = Annotated[AsyncSession, Depends(get_session)]

# OAuth2 схема для получения токена
oauth2_scheme = OAuth2PasswordBearer(
    scheme_name='Аутентификация',
    description='username: email or phone',
    tokenUrl='api/v1/auth/token',
    auto_error=True,
)


async def get_current_user(
    session: SessionDep,
    token: str = Depends(oauth2_scheme),
) -> User:
    """Зависимость, которая извлекает текущего пользователя из токена."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Не удалось проверить учетные данные',
        headers={'WWW-Authenticate': 'Bearer'},
    )

    # Декодируем токен
    payload = decode_token(token)
    if payload is None:
        raise credentials_exception

    # Получаем user_id из токена
    user_id = payload.get('sub')
    if user_id is None:
        raise credentials_exception

    # Ищем пользователя в БД
    user = await user_crud.get(int(user_id), session)
    if user is None:
        raise credentials_exception

    # Проверяем активность пользователя
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Пользователь деактивирован',
        )

    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
