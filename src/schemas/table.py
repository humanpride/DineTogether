from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, PositiveInt

from schemas.cafe import CafeShortInfo


class TableBase(BaseModel):
    """Базовая Pydantic-схема стола."""

    description: str | None = Field(default=None)
    seat_number: PositiveInt

    model_config = ConfigDict(extra='forbid', from_attributes=True)


class TableCreate(TableBase):
    """Схема для создания стола."""


class TableInfo(TableBase):
    """Схема для отображения информации о столе."""

    id: int
    cafe: CafeShortInfo
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TableShortInfo(TableBase):
    """Схема краткой информации о столе."""

    id: int


class TableUpdate(TableBase):
    """Схема обновления информации о столе."""

    seat_number: PositiveInt | None = None
    is_active: bool | None = None
