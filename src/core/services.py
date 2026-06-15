import logging
import uuid
from io import BytesIO

from PIL import Image
from anyio import Path as AsyncPath
from fastapi import UploadFile
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.constants import (
    JPEG_EXTENSION,
    JPEG_QUALITY,
    MEDIA_DIR,
)
from core.logging import log
from crud import media_crud
from schemas import MediaCreate


async def save_media_file(file: UploadFile, session: AsyncSession) -> uuid.UUID:
    """Проверяет, конвертирует в JPEG и сохраняет файл."""
    file_name = f'{uuid.uuid4()}{JPEG_EXTENSION}'
    file_path = MEDIA_DIR / file_name
    try:
        log(logging.DEBUG, f'Создание записи в БД для файла "{file.filename}" с путем "{file_path}"...')
        media = await media_crud.create(
            obj_in=MediaCreate(path=str(file_path)),
            session=session,
        )
    except SQLAlchemyError as error:
        log(logging.CRITICAL, f'Ошибка создания записи в БД: {error}')
        await session.rollback()
        raise

    await session.commit()

    log(logging.DEBUG, f'Запись в БД для файла "{file.filename}" успешно создана с ID `{media.id}`.')
    try:
        log(logging.DEBUG, f'Создание папки "{MEDIA_DIR}" для сохранения файлов...')
        await AsyncPath(MEDIA_DIR).mkdir(parents=True, exist_ok=True)
    except OSError as error:
        log(logging.CRITICAL, f'Не удалось создать папку media: {error}')
        raise
    log(logging.DEBUG, f'Папка "{MEDIA_DIR}" готова для сохранения файлов.')
    try:
        log(logging.DEBUG, f'Получение байтов файла "{file.filename}" для обработки...')
        image_bytes = BytesIO(await file.read())
        log(logging.DEBUG, f'Открываем файл "{file.filename}" как изображение...')
        with Image.open(image_bytes) as image:
            log(
                logging.DEBUG,
                f'Проверяем режим изображения "{file.filename}" ({image.mode}) для конвертации в JPEG...',
            )
            if image.mode in ('RGBA', 'LA', 'P'):
                log(logging.DEBUG, f'Конвертация изображения "{file.filename}" в RGB...')
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    log(
                        logging.DEBUG,
                        (
                            f'Преобразование палитрового изображения "{file.filename}" '
                            'в RGBA для сохранения альфа-канала...'
                        ),
                    )
                    image = image.convert('RGBA')
                if image.mode == 'RGBA':
                    log(
                        logging.DEBUG,
                        f'Сохранение альфа-канала изображения "{file.filename}" при конвертации в JPEG...',
                    )
                    background.paste(image, mask=image.split()[-1])
                else:
                    log(
                        logging.DEBUG,
                        f'Преобразование изображения "{file.filename}" в RGB без сохранения альфа-канала...',
                    )
                    background.paste(image)
                image = background
            elif image.mode != 'RGB':
                log(logging.DEBUG, f'Преобразование изображения "{file.filename}" в RGB...')
                image = image.convert('RGB')
            log(
                logging.DEBUG,
                (
                    f'Сохранение изображения "{file.filename}" в формате JPEG '
                    f'с качеством {JPEG_QUALITY} по пути "{file_path}"...'
                ),
            )
            image.save(file_path, format='JPEG', quality=JPEG_QUALITY)
    except (OSError, ValueError) as error:
        log(logging.CRITICAL, f'Не удалось сохранить файл: {error}')
        await AsyncPath(file_path).unlink(missing_ok=True)
        raise
    finally:
        log(logging.DEBUG, f'Закрываем файл "{file.filename}"...')
        await file.close()

    log(logging.INFO, f'Файл "{file.filename}" успешно сохранен как "{file_path}" с ID `{media.id}`.')
    return media.id
