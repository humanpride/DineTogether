from pydantic import BaseModel, ConfigDict, Field

from core.constants import UserRole


class Token(BaseModel):
    """Схема для выдачи токена доступа."""

    access_token: str = Field(..., description='JWT токен доступа')
    token_type: str = Field(default='bearer', description='Тип токена')

    model_config = ConfigDict(
        from_attributes=True,
        extra='forbid',
    )


class TokenData(BaseModel):
    """Схема данных из JWT токена."""

    user_id: int
    role: UserRole | None

    model_config = ConfigDict(
        from_attributes=True,
        extra='forbid',
    )
