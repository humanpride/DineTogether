from datetime import date, datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, field_validator, model_validator

from core.constants import BookingStatus
from schemas.cafe import CafeShortInfo
from schemas.slot import TimeSlotShortInfo
from schemas.table import TableShortInfo
from schemas.user import UserShortInfo


class BookingTableSlotSchema(BaseModel):
    """Схема пары стол-слот для бронирования."""

    table_id: PositiveInt
    slot_id: PositiveInt

    model_config = ConfigDict(extra='forbid')


class BookingBase(BaseModel):
    """Базовая схема бронирования."""

    tables_slots: list[BookingTableSlotSchema] = Field(min_length=1)
    guest_number: PositiveInt
    note: str | None = None
    booking_date: date

    model_config = ConfigDict(extra='forbid', from_attributes=True)


class BookingCreate(BookingBase):
    """Схема создания бронирования."""

    cafe_id: PositiveInt

    @field_validator('booking_date', mode='after')
    @classmethod
    def validate_booking_date(cls, booking_date: date) -> date:
        """Проверяет, что дата бронирования не в прошлом."""
        if booking_date < date.today():
            raise ValueError('Дата бронирования не может быть в прошлом.')
        return booking_date


class BookingUpdate(BaseModel):
    """Схема частичного обновления бронирования."""

    tables_slots: list[BookingTableSlotSchema] | None = Field(default=None, min_length=1)
    guest_number: PositiveInt | None = None
    note: str | None = None
    status: BookingStatus | None = None
    booking_date: date | None = None
    is_active: bool | None = None

    @model_validator(mode='after')
    def validate_not_empty(self) -> Self:
        """Проверяет, что передано хотя бы одно поле для обновления."""
        if not self.model_fields_set:
            raise ValueError('Для обновления нужно передать хотя бы одно поле.')
        return self


class BookingTableSlotShortInfo(BaseModel):
    """Краткая информация о столе и слоте бронирования."""

    table: TableShortInfo
    slot: TimeSlotShortInfo
    model_config = ConfigDict(from_attributes=True)


class BookingInfo(BaseModel):
    """Полная информация о бронировании."""

    id: int
    user: UserShortInfo
    cafe: CafeShortInfo
    tables_slots: list[BookingTableSlotShortInfo]
    guest_number: PositiveInt
    note: str | None
    status: BookingStatus
    booking_date: date
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
