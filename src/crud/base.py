import logging
from typing import Any, Generic, Optional, Sequence, Type, TypeVar, Union
from uuid import UUID

from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import log

ModelType = TypeVar('ModelType')

CreateSchemaType = TypeVar('CreateSchemaType')

UpdateSchemaType = TypeVar('UpdateSchemaType')


class CRUDBase(
    Generic[
        ModelType,
        CreateSchemaType,
        UpdateSchemaType,
    ],
):
    """Базовый CRUD-класс для работы с SQLAlchemy моделями.

    Generic позволяет указать типы один раз при наследовании:

    Пример:
    ```
        class CRUDUser(
            CRUDBase[
                User,
                UserCreate,
                UserUpdate,
            ]
        ):
            pass

        user_crud = CRUDUser(User)
    ```

    Где:
        * `ModelType` — SQLAlchemy модель
        * `CreateSchemaType` — схема создания
        * `UpdateSchemaType` — схема обновления
    """

    def __init__(self, model: Type[ModelType]) -> None:
        """Инициализирует CRUD-объект."""
        self.model = model

    async def get(
        self,
        obj_id: int | UUID,
        session: AsyncSession,
    ) -> Optional[ModelType]:
        """Получает объект по ID."""
        return (
            (
                await session.execute(
                    select(self.model).where(self.model.id == obj_id),
                )
            )
            .scalars()
            .first()
        )

    async def exists(
        self,
        session: AsyncSession,
        **kwargs: Any,
    ) -> bool:
        """Проверяет существование объекта по критериям."""
        stmt = select(self.model).filter_by(**kwargs).limit(1)
        result = await session.execute(stmt)
        return result.first() is not None

    async def get_one_or_none(
        self,
        session: AsyncSession,
        **kwargs: Any,
    ) -> Optional[ModelType]:
        """Получение одного объекта по фильтрам или None."""
        stmt = select(self.model)
        log(
            logging.DEBUG,
            (f'CRUDBase.get_one_or_none - получение объекта {self.model.__name__} по фильтрам {kwargs}'),
        )
        log(logging.DEBUG, 'Установка фильтров для ORM запроса...')
        for field, value in kwargs.items():
            if value is None:
                log(logging.DEBUG, f'Для поля {field} не установлено значение. Пропуск...')
                continue

            stmt = stmt.where(
                getattr(self.model, field) == value,
            )
        log(logging.DEBUG, 'Выполнение запроса...')
        result = (await session.execute(stmt.limit(1))).scalar_one_or_none()

        log(logging.DEBUG, 'CRUDBase.get_one_or_none - возврат результата')
        return result

    async def get_all(
        self,
        session: AsyncSession,
        **filters: Union[bool, int, str, None],
    ) -> Sequence[ModelType]:
        """Получает список всех объектов."""
        log(logging.DEBUG, f'CRUDBase.get_all - получение всех объектов {self.model.__name__}')
        stmt = select(self.model)
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

        log(logging.DEBUG, 'CRUDBase.get_all - возврат результата')
        return result.scalars().all()

    async def create(
        self,
        obj_in: CreateSchemaType | dict,
        session: AsyncSession,
    ) -> ModelType:
        """Создаёт новый объект."""
        log(logging.DEBUG, f'CRUDBase.create - создание объекта {self.model.__name__}')
        if isinstance(obj_in, dict):
            obj_in_data = obj_in
        else:
            obj_in_data = obj_in.model_dump()

        db_obj = self.model(**obj_in_data)

        session.add(db_obj)
        try:
            await session.flush()
        except IntegrityError as error:
            log(logging.ERROR, f'Ошибка создания записи в БД: {error}\nОткат изменений...')
            await session.rollback()

            raise ValueError(
                f'Ошибка создания {self.model.__name__}',
            )
        log(logging.DEBUG, 'CRUDBase.create - возврат результата')
        return db_obj

    async def update(
        self,
        db_obj: ModelType,
        obj_in: UpdateSchemaType,
        session: AsyncSession,
    ) -> ModelType:
        """Обновляет существующий объект."""
        update_data = obj_in.model_dump(exclude_unset=True)
        log(
            logging.DEBUG,
            (
                f'CRUDBase.update - обновление объекта {self.model.__name__}[{db_obj.id}] '
                f'данными: {update_data}'
            ),
        )
        for field, value in update_data.items():
            #  Лишние поля отсекаются extra_forbiden в схемах pydantic
            setattr(db_obj, field, value)

        session.add(db_obj)
        log(logging.DEBUG, 'CRUDBase.update - сохранение данных в БД')
        await session.flush()

        log(logging.DEBUG, 'CRUDBase.update - возврат результата')
        return db_obj

    async def remove(
        self,
        db_obj: ModelType,
        session: AsyncSession,
    ) -> ModelType:
        """Удаляет объект."""
        log(logging.DEBUG, f'CRUDBase.remove - удаление объекта {self.model.__name__}[{db_obj.id}]')
        await session.delete(db_obj)
        log(logging.DEBUG, 'CRUDBase.remove - объект удалён')
        return db_obj
