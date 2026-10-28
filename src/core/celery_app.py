from celery import Celery

from core.settings import settings

celery_app = Celery(
    'DineTogether',
    broker=settings.celery_broker,
    include=['tasks.email'],
)

celery_app.conf.update(
    # Результаты задач отправки писем приложением не используются.
    task_ignore_result=True,
    # RabbitMQ 4.3+ по умолчанию запрещает non-durable,
    # non-exclusive classic queues.
    control_queue_exclusive=True,
    event_queue_exclusive=True,
)
