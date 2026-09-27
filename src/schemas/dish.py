from datetime import datetime

from pydantic import UUID4, BaseModel, Field, PositiveFloat

from schemas.venue import VenueShortInfo


class DishBase(BaseModel):
    """Базовая схема блюда."""

    name: str = Field(..., max_length=255)
    description: str | None = None
    photo_id: UUID4 | None = None
    price: PositiveFloat


class DishCreate(DishBase):
    """Схема для создания блюда."""

    # блюда не привязаны к кафе, могут быть в меню у нескольких заведений или ни у одного
    venues_id: list[int] | None = Field(None, min_length=1)


class DishUpdate(DishCreate):
    """Схема для обновления блюда."""

    is_active: bool | None = None


class DishInfo(DishBase):
    """Схема для отображения информации о блюде."""

    id: int
    venues: list[VenueShortInfo]
    is_active: bool
    created_at: datetime
    updated_at: datetime
