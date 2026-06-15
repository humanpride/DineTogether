import logging
from typing import Sequence, Union

from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.logging import log
from crud.base import CRUDBase
from models import User
from models.cafe import Cafe
from schemas.cafe import CafeCreate, CafeUpdate


class CRUDCafe(
    CRUDBase[
        Cafe,
        CafeCreate,
        CafeUpdate,
    ],
):
    """CRUD-класс для работы с моделью Cafe."""

    _get_statement = select(Cafe).options(
        selectinload(Cafe.managers),
    )

    async def get(self, cafe_id: int, session: AsyncSession) -> Cafe:
        """Возвращает кафе по его `id` или `None`."""
        return await session.scalar(self._get_statement.where(Cafe.id == cafe_id))

    async def get_all(
        self,
        session: AsyncSession,
        **filters: Union[bool, int, str, None],
    ) -> Sequence[Cafe]:
        """Получает список всех кафе."""
        log(logging.DEBUG, f'CRUDCafe.get_all - получение всех объектов {self.model.__name__}')
        stmt = self._get_statement
        mapper_attrs = inspect(self.model).attrs
        log(logging.DEBUG, 'Установка фильтров для ORM запроса...')
        for field, value in filters.items():
            if value is None:
                log(logging.DEBUG, f'Для поля {field} не установлено значение. Пропуск...')
                continue
            if field not in mapper_attrs:
                message = f"Поле '{field}' отсутствует в модели {self.model.__name__}"
                log(logging.ERROR, message)
                raise ValueError(message)
            stmt = stmt.where(
                getattr(self.model, field) == value,
            )
        stmt = stmt.order_by(self.model.id)

        log(logging.DEBUG, 'Выполнение запроса...')
        result = await session.execute(stmt)

        log(logging.DEBUG, 'CRUDCafe.get_all - возврат результата')
        return result.scalars().all()

    async def create(self, obj_in: CafeCreate, session: AsyncSession) -> Cafe:
        """Создаёт кафе и назначает менеджеров."""
        cafe_data = obj_in.model_dump(
            exclude={'manager_ids'},
        )
        users = (
            await session.scalars(
                select(User).where(User.id.in_(obj_in.manager_ids)),
            )
        ).all()

        cafe = Cafe(
            managers=users,
            **cafe_data,
        )
        session.add(cafe)
        await session.flush()

        return cafe

    async def get_managers_emails(
        self,
        cafe: Cafe,
        session: AsyncSession,
    ) -> list[str]:
        """Возвращает email всех менеджеров кафе."""
        return [manager.email for manager in cafe.managers if manager.email]

    async def update(self, db_obj: Cafe, obj_in: CafeUpdate, session: AsyncSession) -> Cafe:
        """Обновляет кафе и назначает менеджеров."""
        cafe_data = obj_in.model_dump(
            exclude={'manager_ids'},
            exclude_unset=True,
        )
        log(
            logging.DEBUG,
            (f'CRUDCafe.update - обновление объекта Cafe[{db_obj.id}] данными: {cafe_data}'),
        )
        for field, value in cafe_data.items():
            #  Лишние поля отсекаются extra_forbiden в схемах pydantic
            setattr(db_obj, field, value)

        if obj_in.manager_ids is not None:
            db_obj.managers.clear()
            db_obj.managers.extend(
                (
                    await session.scalars(
                        select(User).where(User.id.in_(obj_in.manager_ids)),
                    )
                ).all(),
            )
        await session.flush()

        return db_obj


cafe_crud = CRUDCafe(Cafe)
