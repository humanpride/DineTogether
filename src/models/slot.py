from datetime import time
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Text, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.base_model import Base
from core.constants import SLOT_TIME_FORMAT

if TYPE_CHECKING:
    from models.cafe import Cafe


class TimeSlot(Base):
    """Модель временного слота для  брони места в кафе."""

    cafe_id: Mapped[int] = mapped_column(
        ForeignKey(
            'cafes.id',
            ondelete='CASCADE',
        ),
        nullable=False,
        comment='ID кафе',
    )
    start_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
        comment='Время начала слота',
    )
    end_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
        comment='Время окончания слота',
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment='Описание слота',
    )
    cafe: Mapped['Cafe'] = relationship(lazy='selectin')

    __table_args__ = (
        CheckConstraint(
            'end_time > start_time',
            name='check_time_order',
        ),
        UniqueConstraint(
            'cafe_id',
            'start_time',
            'end_time',
            name='uq_cafe_timeslot',
        ),
    )

    def __repr__(self) -> str:
        """Возвращает строковое представление экземпляра TimeSlot."""
        return (
            f'<{self.__class__.__name__}('
            f'id={self.id}, '
            f'cafe_id={self.cafe_id}, '
            f'start_time={self.start_time.strftime(SLOT_TIME_FORMAT)}, '
            f'end_time={self.end_time.strftime(SLOT_TIME_FORMAT)})>'
        )
