from fastapi import APIRouter

from api.endpoints import (
    auth_router,
    booking_router,
    # dish_router,
    media_router,
    slot_router,
    table_router,
    user_router,
    venue_router,
)

main_router = APIRouter(prefix='/api/v1')

# теги прописываем здесь потому, что
# управлять всеми тегами (добавлять/удалять/изменять) проще в 1 месте
main_router.include_router(auth_router, tags=['Authentication'])
main_router.include_router(booking_router, tags=['Bookings'])
main_router.include_router(venue_router, tags=['Venues'])
# main_router.include_router(dish_router, tags=['Dishes'])
main_router.include_router(media_router, tags=['Media'])
main_router.include_router(slot_router, tags=['Time slots'])
main_router.include_router(table_router, tags=['Tables'])
main_router.include_router(user_router, tags=['Users'])
