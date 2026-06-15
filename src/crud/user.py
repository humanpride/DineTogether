from sqlalchemy.ext.asyncio import AsyncSession

from core.security import get_password_hash
from crud.base import CRUDBase
from models import User
from schemas.user import UserCreate


class CRUDUser(CRUDBase):
    """CRUD операции для модели User."""

    async def create_user(
        self,
        obj_in: UserCreate,
        session: AsyncSession,
    ) -> User:
        """Создание нового пользователя c хешированным паролем."""
        user_data = obj_in.model_dump(exclude={'password'})
        user_data['hashed_password'] = get_password_hash(obj_in.password)

        db_obj = User(**user_data)

        session.add(db_obj)
        await session.flush()

        return db_obj


user_crud = CRUDUser(User)
