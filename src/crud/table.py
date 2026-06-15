from crud.base import CRUDBase
from models import Table


class CRUDTable(CRUDBase):
    """CRUD-класс для работы с моделью Table."""


table_crud = CRUDTable(Table)
