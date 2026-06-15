from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Настройки приложения."""

    # Общие настройки.
    title: str = 'DineTogether'
    version: str = '2.0.0'
    description: str = 'Сервис бронирования мест в кафе'
    secret_key: str
    algorithm: str = 'HS256'
    access_token_expire_minutes: int = 1440

    # Настройки дефолтного админа
    admin_email: str
    admin_username: str
    admin_password: str

    # Настройки подключения к БД.
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_server: str = 'localhost'
    postgres_port: int = 5432

    #  Настройки для работы Celery.
    celery_broker: str

    #  Настройки для отправки email.
    from_email: str
    smtp_host: str
    smtp_port: int

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / '../infra/.env',
        env_file_encoding='utf-8',
        extra='ignore',
        case_sensitive=False,
    )

    @property
    def db_url(self) -> str:
        """Строка подключения к БД."""
        return (
            f'postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@'
            f'{self.postgres_server}:{self.postgres_port}/{self.postgres_db}'
        )


settings = Settings()
