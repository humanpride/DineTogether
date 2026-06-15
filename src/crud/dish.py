from crud.base import CRUDBase
from models.dish import Dish
from schemas.dish import DishCreate, DishUpdate


class CRUDDish(CRUDBase[Dish, DishCreate, DishUpdate]):
    """CRUD-класс для работы с моделью Dish."""


dish_crud = CRUDDish(Dish)
