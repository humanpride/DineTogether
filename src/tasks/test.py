from core.celery_app import celery_app


@celery_app.task
def hello() -> str:
    """Тестовая задача."""
    print('Hello Celery')
