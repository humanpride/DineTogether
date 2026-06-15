from core.constants import UserRole
from core.dependencies import session_maker
from core.settings import settings
from crud.user import user_crud
from schemas.user import UserCreate


async def init_default_admin() -> None:
    """Создает дефолтного администратора при старте, если его нет."""
    async with session_maker() as session:
        if await user_crud.exists(
            session=session,
            email=settings.admin_email,
        ):
            return

        admin = await user_crud.create_user(
            obj_in=UserCreate(
                username=settings.admin_username,
                email=settings.admin_email,
                phone=None,
                password=settings.admin_password,
                role=UserRole.ADMIN,
                is_active=True,
            ),
            session=session,
        )
        await session.commit()

        print('Дефолтный администратор создан!')
        print(f'Username: {admin.username}')
        print(f'Email: {admin.email}')
        print(f'Password: {settings.admin_password}')
