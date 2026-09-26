from datetime import datetime

from pydantic import UUID4, BaseModel, ConfigDict, Field

from schemas.user import RussianPhone, UserShortInfo


class VenueBase(BaseModel):
    """Базовая Pydantic-схема кафе."""

    name: str = Field(max_length=255)
    address: str = Field(max_length=255)
    phone: RussianPhone | None = None
    timezone: str = Field(max_length=64, description='IANA timezone, for example Europe/Berlin')
    description: str | None = None
    photo_id: UUID4 | None = None

    model_config = ConfigDict(
        from_attributes=True,
        extra='forbid',
    )


class VenueCreate(VenueBase):
    """Схема для создания кафе."""

    manager_ids: list[int] = Field(..., min_length=1, description='Список менеджеров кафе')


class VenueInfo(VenueBase):
    """Схема для отображения информации о кафе."""

    id: int
    managers: list[UserShortInfo]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class VenueShortInfo(VenueBase):
    """Схема краткой информации о кафе."""

    id: int


class VenueUpdate(VenueBase):
    """Схема обновления информации о кафе."""

    name: str | None = Field(None, min_length=1, max_length=255)
    address: str | None = Field(None, min_length=5, max_length=255)
    is_active: bool | None = None
    manager_ids: list[int] | None = Field(None, min_length=1, description='Список менеджеров кафе')
