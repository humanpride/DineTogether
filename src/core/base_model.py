from datetime import datetime, timezone

from sqlalchemy import BOOLEAN, DateTime, Integer, func
from sqlalchemy.orm import Mapped, declarative_base, declared_attr, mapped_column


def get_utc_now() -> datetime:
    """Return the current UTC datetime."""
    return datetime.now(timezone.utc)


class PreBase:
    """Base class for all database models."""

    @declared_attr
    def __tablename__(cls) -> str:  # noqa: N805
        """Return the table name derived from the class name."""
        return f'{cls.__name__.lower()}s'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    is_active: Mapped[bool] = mapped_column(BOOLEAN, default=True, server_default='true')
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=get_utc_now,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=get_utc_now,
        server_onupdate=func.now(),
    )


Base = declarative_base(cls=PreBase)
