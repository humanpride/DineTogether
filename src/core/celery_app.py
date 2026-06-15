from celery import Celery

from core.settings import settings

# Настройки celery.
celery_app = Celery(
    'DineTogether',
    broker=settings.celery_broker,
    backend='rpc://',  # Сделал только для тестирования.
    include=['tasks.test', 'tasks.email'],
    # TODO: backend='redis://localhost'
)

# Эти команды нужны для того, чтобы запутить брокер при деплои на сервер.
# Запуск Celery командой celery --app core.celery_app worker --pool threads --loglevel INFO.
# Запуск Flower командой celery --app core.celery_app flower.
