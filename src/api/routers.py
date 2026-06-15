from fastapi import APIRouter

from api.endpoints import (
    auth_router,
    booking_router,
    cafe_router,
    dish_router,
    media_router,
    slot_router,
    table_router,
    user_router,
)

main_router = APIRouter(prefix='/api/v1')

# теги прописываем здесь потому, что
# управлять всеми тегами (добавлять/удалять/изменять) проще в 1 месте
main_router.include_router(auth_router, tags=['Аутентификация'])
main_router.include_router(booking_router, tags=['Бронирования'])
main_router.include_router(cafe_router, tags=['Кафе'])
main_router.include_router(dish_router, tags=['Блюда'])
main_router.include_router(media_router, tags=['Медиа'])
main_router.include_router(slot_router, tags=['Временные слоты'])
main_router.include_router(table_router, tags=['Столы'])
main_router.include_router(user_router, tags=['Пользователи'])
