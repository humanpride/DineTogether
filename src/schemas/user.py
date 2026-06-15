from datetime import datetime
from typing import Annotated, Optional

import phonenumbers
from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    EmailStr,
    Field,
    TypeAdapter,
    ValidationError,
)

from core.constants import UserRole


def normalize_ru_phone(value: str) -> str:
    """Нормализует российские и международные номера телефонов в формат E.164."""
    try:
        parsed_phone = phonenumbers.parse(
            number=value,
            region=None if value.startswith('+') else 'RU',
        )
        if not (phonenumbers.is_valid_number(parsed_phone) and phonenumbers.is_possible_number(parsed_phone)):
            # невалидный номер телефона
            raise ValueError('Недопустимый номер телефона')
        return phonenumbers.format_number(parsed_phone, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException:
        # ошибка парсинга номера телефона
        raise ValueError('Недопустимый номер телефона')


RussianPhone = Annotated[str, BeforeValidator(normalize_ru_phone)]

email_adapter = TypeAdapter(EmailStr)
phone_adapter = TypeAdapter(RussianPhone)


async def is_email(value: str) -> bool:
    """Определяет, является ли строка валидным адресом электронной почты."""
    try:
        email_adapter.validate_python(value)
        return True
    except ValidationError:
        return False


async def is_phone(value: str) -> bool:
    """Определяет, является ли строка валидным номером телефона."""
    try:
        phone_adapter.validate_python(value)
        return True
    except ValidationError:
        return False


async def login_field_data(login: str) -> dict[str, str]:
    """Возвращает тип и значение логина."""
    if await is_email(login):
        return {'email': login}
    if await is_phone(login):
        return {'phone': normalize_ru_phone(login)}
    raise ValueError('Логин не является телефоном или email')


def _validate_login(value: str) -> str:
    if is_email(value) or is_phone(value):
        return value
    # если строка не подошла ни к одному типу - исключение
    raise ValueError('Поле login должно содержать корректный email или номер телефона')


LoginField = Annotated[
    str,
    BeforeValidator(_validate_login),
]


class BaseUserData(BaseModel):
    """Базовый класс для данных пользователя."""

    username: str = Field(..., min_length=3, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[RussianPhone] = None
    telegram_id: str | None = None

    model_config = ConfigDict(
        from_attributes=True,
        extra='forbid',
    )


class UserLogin(BaseModel):
    """Схема для аутентификации пользователя."""

    login: LoginField
    password: str = Field(..., min_length=5, max_length=50, description='Пароль')

    model_config = ConfigDict(
        extra='forbid',
    )


class UserShortInfo(BaseUserData):
    """Схема с данными пользователя."""

    id: int


class UserInfo(UserShortInfo):
    """Схема с полными данными пользователя."""

    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserRegister(BaseUserData):
    """Схема регистрации пользователя."""

    password: str = Field(..., min_length=5, max_length=50, description='Пароль, от 5 до 50 знаков')


class UserCreate(UserRegister):
    """Схема для создания пользователя."""

    role: UserRole = Field(default=UserRole.USER, description='Роль пользователя')
    is_active: bool = True


class UserUpdateMe(BaseUserData):
    """Схема для обновления профиля пользователем самому."""

    username: Optional[str] = Field(None, min_length=3, max_length=100)


class UserUpdate(UserUpdateMe):
    """Схема для обновления данных пользователя."""

    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserChangePassword(BaseModel):
    """Схема для смены пароля."""

    old_password: str = Field(..., min_length=5, max_length=50, description='Старый пароль')
    new_password: str = Field(..., min_length=5, max_length=50, description='Новый пароль')

    model_config = ConfigDict(
        extra='forbid',
    )


class UserUpdateDBPassword(BaseModel):
    """Схема для обновления только пароля."""

    hashed_password: str

    model_config = ConfigDict(
        extra='forbid',
    )


class UserDeactivate(BaseModel):
    """Схема для деактивации и активации пользователей."""

    is_active: bool = False

    model_config = ConfigDict(
        extra='forbid',
    )
