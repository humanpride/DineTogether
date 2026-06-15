import uuid

from pydantic import BaseModel, Field


class MediaCreate(BaseModel):
    """Схема для создания записи о медиафайле в БД."""

    path: str = Field(..., description='Путь к сохраненному файлу')


class MediaUploaded(BaseModel):
    """Схема для ответа после успешной загрузки файла."""

    media_id: uuid.UUID
