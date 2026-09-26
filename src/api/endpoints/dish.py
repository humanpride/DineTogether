from typing import Any, Sequence

from fastapi import APIRouter, HTTPException, status

from core.dependencies import CurrentUserDep, SessionDep
from core.validators import validate_current_manager_or_admin, validate_venue_ids
from crud.dish import dish_crud
from schemas.dish import DishCreate, DishInfo, DishUpdate

router = APIRouter(prefix='/dishes')


@router.get('/', response_model=list[DishInfo])
async def get_all_dishes(
    session: SessionDep,
    user: CurrentUserDep,
    show_active: bool | None = None,
    venue_id: int | None = None,
) -> Sequence[DishInfo]:
    """Get a list of dishes."""
    filters: dict[str, Any] = dict()
    if user.role == 'USER':
        filters['is_active'] = True
    else:
        filters['is_active'] = show_active

    if venue_id:
        filters['venue_id'] = venue_id

    return await dish_crud.get_all(session=session, **filters)


@router.post('/', response_model=DishInfo, status_code=status.HTTP_201_CREATED)
async def create_dish(
    dish_in: DishCreate,
    session: SessionDep,
    user: CurrentUserDep,
) -> DishInfo:
    """Create a new dish. Only for administrators and managers."""
    validate_current_manager_or_admin(user)
    await validate_venue_ids(dish_in.venues_id, session)

    new_dish = await dish_crud.create(dish_in, session)
    await session.commit()
    await session.refresh(new_dish, attribute_names=['venues'])

    return new_dish


@router.get('/{dish_id}', response_model=DishInfo)
async def get_dish(
    dish_id: int,
    session: SessionDep,
    user: CurrentUserDep,
) -> DishInfo:
    """Get information about a dish by its ID."""
    dish = await dish_crud.get(dish_id, session)
    if not dish or user.role == 'USER' and not dish.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Dish not found',
        )

    return dish


@router.patch('/{dish_id}', response_model=DishInfo)
async def update_dish(
    dish_id: int,
    dish_in: DishUpdate,
    session: SessionDep,
    user: CurrentUserDep,
) -> DishInfo:
    """Update information about a dish by its ID. Only for administrators and managers."""
    validate_current_manager_or_admin(user)
    dish = await dish_crud.get(dish_id, session)
    if not dish:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Dish not found',
        )

    updated_dish = await dish_crud.update(dish, dish_in, session)
    await session.commit()
    await session.refresh(update_dish, attribute_names=['venues'])

    return updated_dish
