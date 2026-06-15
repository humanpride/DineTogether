from crud.base import CRUDBase
from models.slot import TimeSlot
from schemas.slot import TimeSlotCreate, TimeSlotUpdate


class CRUDSlot(CRUDBase[TimeSlot, TimeSlotCreate, TimeSlotUpdate]):
    """CRUD-класс для работы с моделью Slot."""


slot_crud = CRUDSlot(TimeSlot)
