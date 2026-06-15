import logging
import sys
from logging.handlers import RotatingFileHandler
from typing import Any

from core.constants import (
    DATE_FORMAT,
    LOG_BACKUP_COUNT,
    LOG_DEFAULT_LEVEL,
    LOG_DIR_PATH,
    LOG_ENCODING,
    LOG_FILE_PATH,
    LOG_FORMAT,
    LOG_MAX_BYTES,
)

logger = logging.getLogger('app')


def setup_logging() -> None:
    """Настройка глобального логирования."""
    LOG_DIR_PATH.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(LOG_DEFAULT_LEVEL)
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        filename=LOG_FILE_PATH,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding=LOG_ENCODING,
    )
    file_handler.setLevel(LOG_DEFAULT_LEVEL)
    file_handler.setFormatter(formatter)

    logger.setLevel(LOG_DEFAULT_LEVEL)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)


def log(level: int, message: str, actor: Any = None) -> None:
    """Универсальная функция логирования.

    Args:
        level: Уровень логирования (`logging.INFO`, `logging.ERROR`, etc.)
        message: Сообщение для лога
        actor: Пользователь (объект `User`, строка или `None`)

    """
    if actor is None:
        actor_str = 'SYSTEM'
    elif isinstance(actor, str):
        actor_str = actor
    else:
        actor_str = f'{actor.username} {actor.id}'

    logger.log(level, message, extra={'actor': actor_str})
