import uuid

from sqlalchemy import UUID, String
from sqlalchemy.orm import Mapped, mapped_column

from core.base_model import Base


class Media(Base):
    """Модель загруженного файла на сервере.

    Поля:
        * id: UUID
        * path: str (относительный путь к файлу на сервере)

    Внутри `path` может храниться просто название файла (тогда файл находится в папке `media`)

    А также путь к файлу, например `images/avatars/{uuid}.jpg`, тогда полный путь будет
    `media/images/avatars/{uuid}.jpg`.
    """

    __tablename__ = 'media_files'

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    path: Mapped[str] = mapped_column(String(512))
