from datetime import datetime, time
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, model_validator

from core.constants import SLOT_TIME_FORMAT
from schemas.cafe import CafeShortInfo

StartTime = Annotated[
    time,
    Field(
        description='Время начала слота',
    ),
]

EndTime = Annotated[
    time,
    Field(
        description='Время окончания слота',
    ),
]


class TimeSlotBase(BaseModel):
    """Базовая схема слота."""

    start_time: StartTime
    end_time: EndTime
    description: str | None = Field(
        None,
        description='Описание слота',
    )

    model_config = ConfigDict(
        extra='forbid',
        from_attributes=True,
    )


class TimeSlotCreate(TimeSlotBase):
    """Схема для создания слота."""

    @model_validator(mode='after')
    def validate_time_slot(self) -> Self:
        """Валидирует время начала слота."""
        if all([self.start_time, self.end_time]) and self.start_time >= self.end_time:
            raise ValueError(
                f'Время начала бронирования '
                f'{self.start_time.strftime(SLOT_TIME_FORMAT)} '
                f'должно быть раньше окончания '
                f'{self.end_time.strftime(SLOT_TIME_FORMAT)}!',
            )
        return self


class TimeSlotUpdate(TimeSlotCreate):
    """Схема для частичного обновления слота."""

    start_time: StartTime | None = None
    end_time: EndTime | None = None
    is_active: bool | None = Field(
        None,
        description='Статус слота',
    )

    @model_validator(mode='after')
    def validate_empty_fields(self) -> Self:
        """Валидирует наличие информации для обновления."""
        if not self.model_fields_set:
            error_msg = 'Для обновления необходимо изменить хотя бы одно поле!'
            raise ValueError(error_msg)
        return self


class TimeSlotShortInfo(TimeSlotBase):
    """Схема короткой информации о слоте."""

    id: PositiveInt = Field(
        ...,
        description='ID слота',
    )


class TimeSlotInfo(TimeSlotShortInfo):
    """Схема полной информации о слоте."""

    cafe: CafeShortInfo = Field(
        ...,
        description='Информация о кафе бронирования',
    )
    is_active: bool = Field(
        ...,
        description='Флаг активности слота',
    )
    created_at: datetime = Field(
        ...,
        description='Создано',
    )
    updated_at: datetime = Field(
        ...,
        description='Обновлено',
    )
