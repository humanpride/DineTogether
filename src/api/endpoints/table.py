import logging
from typing import Sequence

from fastapi import APIRouter, HTTPException, status

from core.constants import UserRole
from core.dependencies import CurrentUserDep, SessionDep
from core.logging import log
from core.validators import (
    validate_current_manager_or_admin,
    validate_existed_venue,
)
from crud.table import table_crud
from schemas.table import TableCreate, TableInfo, TableUpdate

router = APIRouter(prefix='/venues/{venue_id}/tables')


@router.get(
    '/',
    response_model=list[TableInfo],
    response_model_exclude_none=True,
)
async def get_all_tables(
    venue_id: int,
    session: SessionDep,
    user: CurrentUserDep,
    show_active: bool | None = None,
) -> Sequence[TableInfo]:
    """Return a list of tables in the venue.

    By default:
    - for users - only active tables in the venue (always, regardless of the parameter value)
    - for administrators - all tables in the venue (both active and inactive)
    - for managers - active tables in the venue

    **show_active:**
    - True - Active tables only
    - False - Inactive tables only
    - None - All tables in the venue
    """
    venue = await validate_existed_venue(venue_id, session)
    if user.role == UserRole.USER:
        show_active = True
    return await table_crud.get_all(
        session=session,
        venue_id=venue.id,
        is_active=show_active,
    )


@router.post(
    '/',
    response_model=TableInfo,
    status_code=status.HTTP_201_CREATED,
)
async def create_new_table(
    venue_id: int,
    table_in: TableCreate,
    session: SessionDep,
    user: CurrentUserDep,
) -> TableInfo:
    """Create a new table in the venue.

    Only for administrators and managers.
    """
    validate_current_manager_or_admin(user)
    venue = await validate_existed_venue(venue_id, session)
    table_data = table_in.model_dump()
    table_data['venue_id'] = venue.id
    new_table = await table_crud.create(
        obj_in=table_data,
        session=session,
    )
    await session.commit()
    await session.refresh(new_table, attribute_names=['venue'])

    return new_table


@router.get(
    '/{table_id}',
    response_model=TableInfo,
)
async def get_table(
    venue_id: int,
    table_id: int,
    session: SessionDep,
    user: CurrentUserDep,
    show_active: bool | None = None,
) -> TableInfo:
    """Get information about a table in the venue by its ID.

    For administrators and managers - all tables, for users - active tables only.

    **show_active:**
    - True - Active tables only
    - False - Inactive tables only
    - None - All tables in the venue (both active and inactive)
    """
    venue = await validate_existed_venue(venue_id, session)

    if user.role == UserRole.USER:
        show_active = True

    table = await table_crud.get_one_or_none(
        session=session,
        id=table_id,
        venue_id=venue.id,
        is_active=show_active,
    )

    if table is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Table not found',
        )
    return table


@router.patch(
    '/{table_id}',
    response_model=TableInfo,
)
async def update_table(
    venue_id: int,
    table_id: int,
    table_in: TableUpdate,
    session: SessionDep,
    user: CurrentUserDep,
) -> TableInfo:
    """Update information about a table in the venue by its ID.

    Access: `ADMIN`/`MANAGER`
    """
    validate_current_manager_or_admin(user)
    venue = await validate_existed_venue(venue_id, session)
    table = await table_crud.get_one_or_none(
        session=session,
        id=table_id,
        venue_id=venue.id,
    )
    if table is None:
        log(
            logging.INFO,
            f'Table with id={table_id} not found or does not belong to venue {venue.id}',
            actor=user,
        )
        raise HTTPException(
            status_code=404,
            detail='Table not found',
        )
    updated_table = await table_crud.update(
        db_obj=table,
        obj_in=table_in,
        session=session,
    )
    await session.commit()

    return updated_table
