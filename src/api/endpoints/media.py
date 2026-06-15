import logging
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.exc import SQLAlchemyError

from core.dependencies import CurrentUserDep, SessionDep
from core.logging import log
from core.services import save_media_file
from core.validators import validate_file
from crud.media import media_crud
from schemas import MediaUploaded

router = APIRouter(prefix='/media')


@router.get(
    '/{media_id}',
    response_class=FileResponse,
    responses={
        status.HTTP_200_OK: {'description': 'Returns image in binary format'},
        status.HTTP_404_NOT_FOUND: {'description': 'Media not found'},
    },
)
async def get_media(
    media_id: uuid.UUID,
    session: SessionDep,
) -> FileResponse:
    """Return stored media file by ID."""
    media = await media_crud.get(media_id, session)
    if media is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Media not found',
        )

    return FileResponse(path=media.path)


@router.post(
    '/',
    response_model=MediaUploaded,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {'description': 'Invalid request parameters'},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {'description': 'Could not save file'},
    },
)
async def upload_media(
    session: SessionDep,
    user: CurrentUserDep,
    file: UploadFile = File(..., description='Загружаемый файл'),
) -> MediaUploaded:
    """Upload image to the server."""
    try:
        log(
            logging.INFO,
            (
                f'Получен запрос на загрузку файла "{file.filename}" '
                f'с content_type "{file.content_type}" '
                f'и размером {getattr(file, "size", "unknown")} байт.'
            ),
            actor=user,
        )
        log(logging.INFO, 'Обработка файла...')
        # коммит сессии происходит внутри save_media_file()
        return MediaUploaded(
            media_id=await save_media_file(
                file=validate_file(file),
                session=session,
            ),
        )
    except (OSError, SQLAlchemyError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
