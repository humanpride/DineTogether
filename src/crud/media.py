from crud.base import CRUDBase
from models.media import Media
from schemas.media import MediaCreate


class CRUDMedia(CRUDBase[Media, MediaCreate, MediaCreate]):
    """CRUD operations for media files."""


media_crud = CRUDMedia(Media)
