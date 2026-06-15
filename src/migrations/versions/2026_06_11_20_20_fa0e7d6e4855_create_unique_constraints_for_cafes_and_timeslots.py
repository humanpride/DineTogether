"""create unique constraints for cafes and timeslots

Revision ID: fa0e7d6e4855
Revises: 71cc279c2f5a
Create Date: 2026-06-11 20:20:21.271295

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fa0e7d6e4855'
down_revision: Union[str, Sequence[str], None] = '71cc279c2f5a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_unique_constraint(None, 'cafes', ['name'])
    op.create_unique_constraint('uq_cafe_timeslot', 'timeslots', ['cafe_id', 'start_time', 'end_time'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('uq_cafe_timeslot', 'timeslots', type_='unique')
    op.drop_constraint(None, 'cafes', type_='unique')
