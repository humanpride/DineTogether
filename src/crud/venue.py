import logging
from typing import Sequence, Union

from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.logging import log
from crud.base import CRUDBase
from models import User
from models.venue import Venue
from schemas.venue import VenueCreate, VenueUpdate


class CRUDVenue(
    CRUDBase[
        Venue,
        VenueCreate,
        VenueUpdate,
    ],
):
    """CRUD-класс для работы с моделью Venue."""

    _get_statement = select(Venue).options(
        selectinload(Venue.managers),
    )

    async def get(self, venue_id: int, session: AsyncSession) -> Venue:
        """Возвращает кафе по его `id` или `None`."""
        return await session.scalar(self._get_statement.where(Venue.id == venue_id))

    async def get_all(
        self,
        session: AsyncSession,
        **filters: Union[bool, int, str, None],
    ) -> Sequence[Venue]:
        """Получает список всех кафе."""
        log(logging.DEBUG, f'CRUDVenue.get_all - получение всех объектов {self.model.__name__}')
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

        log(logging.DEBUG, 'CRUDVenue.get_all - возврат результата')
        return result.scalars().all()

    async def create(self, obj_in: VenueCreate, session: AsyncSession) -> Venue:
        """Создаёт кафе и назначает менеджеров."""
        venue_data = obj_in.model_dump(
            exclude={'manager_ids'},
        )
        users = (
            await session.scalars(
                select(User).where(User.id.in_(obj_in.manager_ids)),
            )
        ).all()

        venue = Venue(
            managers=users,
            **venue_data,
        )
        session.add(venue)
        await session.flush()

        return venue

    async def get_managers_emails(
        self,
        venue: Venue,
        session: AsyncSession,
    ) -> list[str]:
        """Возвращает email всех менеджеров кафе."""
        return [manager.email for manager in venue.managers if manager.email]

    async def update(self, db_obj: Venue, obj_in: VenueUpdate, session: AsyncSession) -> Venue:
        """Обновляет кафе и назначает менеджеров."""
        venue_data = obj_in.model_dump(
            exclude={'manager_ids'},
            exclude_unset=True,
        )
        log(
            logging.DEBUG,
            (f'CRUDVenue.update - обновление объекта Venue[{db_obj.id}] данными: {venue_data}'),
        )
        for field, value in venue_data.items():
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


venue_crud = CRUDVenue(Venue)
