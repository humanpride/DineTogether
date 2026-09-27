import logging
import traceback
from typing import Annotated, AsyncIterator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import session_maker
from core.logging import log
from core.security import decode_token
from crud.user import user_crud
from models.user import User


async def get_session() -> AsyncIterator[AsyncSession]:
    """Provide an asynchronous database session for FastAPI dependencies."""
    session = session_maker()
    try:
        yield session
        await session.commit()
    except SQLAlchemyError as exc:
        await session.rollback()
        log(
            logging.ERROR,
            f'Database error: {exc}',
        )
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Database error',
        )
    finally:
        await session.close()


SessionDep = Annotated[AsyncSession, Depends(get_session)]

oauth2_scheme = OAuth2PasswordBearer(
    scheme_name='Authentication',
    description='username: email or phone',
    tokenUrl='api/v1/auth/token',
    auto_error=True,
)


async def get_current_user(
    session: SessionDep,
    token: str = Depends(oauth2_scheme),
) -> User:
    """Extract the current user from the token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Unable to verify credentials',
        headers={'WWW-Authenticate': 'Bearer'},
    )

    payload = decode_token(token)
    if payload is None:
        raise credentials_exception

    user_id = payload.get('sub')
    if user_id is None:
        raise credentials_exception

    user = await user_crud.get(int(user_id), session)
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='User deactivated',
        )

    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
