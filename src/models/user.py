from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.base_model import Base
from core.constants import UserRole

if TYPE_CHECKING:
    from models import Cafe


class User(Base):
    """Модель пользователя."""

    email: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
        index=True,
    )
    username: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )
    phone: Mapped[str | None] = mapped_column(
        String(20),
        unique=True,
        nullable=True,
    )
    telegram_id: Mapped[str | None] = mapped_column(
        String(50),
        unique=True,
        nullable=True,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name='user_roles'),
        default=UserRole.USER,
        nullable=False,
    )
    cafe_id: Mapped[int | None] = mapped_column(
        ForeignKey('cafes.id'),
        nullable=True,
    )
    cafe: Mapped['Cafe | None'] = relationship(back_populates='managers')
