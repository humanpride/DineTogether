import uuid

from sqlalchemy import UUID, String
from sqlalchemy.orm import Mapped, mapped_column

from core.base_model import Base


class Media(Base):
    """Represent a file uploaded and stored on the server.

    Attributes:
        id: Unique identifier of the file.
        path: Relative path to the file on the server.

    The `path` field can contain either a filename (for files stored directly
    in the `media` directory) or a nested path, for example:
    `images/avatars/{uuid}.jpg`.

    In the latter case, the full file path will be:
    `media/images/avatars/{uuid}.jpg`.

    """

    __tablename__ = 'media_files'

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    path: Mapped[str] = mapped_column(String(512))
