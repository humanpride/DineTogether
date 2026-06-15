"""Константы проекта.

Для объявления путей используется `pathlib`,
для работы с файловой системой - `anyio`.
"""

import logging
from enum import StrEnum
from pathlib import Path

# Пути в проекте
BASE_DIR = Path(__file__).resolve().parent.parent
MEDIA_DIR = BASE_DIR / 'media'
LOG_DIR_PATH = BASE_DIR / 'logs'
LOG_FILE_PATH = LOG_DIR_PATH / 'app.log'

# Логирование
LOG_ENCODING = 'utf-8'
LOG_MAX_BYTES = 10 * 1024 * 1024
LOG_BACKUP_COUNT = 10
LOG_DEFAULT_LEVEL = logging.DEBUG
DATE_FORMAT = '%d.%m.%Y %H:%M:%S'
LOG_FORMAT = '%(asctime)s [%(levelname)s] [%(actor)s]: %(message)s'

# Time Slots
SLOT_TIME_FORMAT: str = '%H:%M'

# Media
ALLOWED_MEDIA_CONTENT_TYPES = {'image/jpeg', 'image/png'}
ALLOWED_MEDIA_EXTENSIONS = {'jpg', 'jpeg', 'png'}
ALLOWED_FORMATS = {'JPEG', 'PNG'}
MAX_MEDIA_SIZE = 5 * 1024 * 1024
INVALID_IMAGE_FORMAT = 'Ожидается jpg или png формат изображения'
INVALID_IMAGE_SIZE = 'Поддерживаются файлы размером до 5 МБ'
JPEG_QUALITY = 85
JPEG_CONTENT_TYPE = 'image/jpeg'
JPEG_EXTENSION = '.jpg'


# Роли пользователей
class UserRole(StrEnum):
    """Роли пользователей в системе."""

    ADMIN = 'ADMIN'
    MANAGER = 'MANAGER'
    USER = 'USER'


# Booking
class BookingStatus(StrEnum):
    """Статусы бронирования."""

    BOOKING = 'BOOKING'
    CANCELED = 'CANCELED'
    ACTIVE = 'ACTIVE'
    COMPLETED = 'COMPLETED'
