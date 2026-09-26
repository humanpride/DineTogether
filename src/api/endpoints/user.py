import logging
from typing import Sequence

from fastapi import APIRouter, HTTPException, Query, status

from core.constants import UserRole
from core.dependencies import CurrentUserDep, SessionDep
from core.logging import log
from core.validators import (
    validate_current_admin,
    validate_current_manager_or_admin,
    validate_unique_email,
    validate_unique_phone,
    validate_unique_username,
)
from crud.user import user_crud
from schemas.user import (
    UserCreate,
    UserDeactivate,
    UserInfo,
    UserShortInfo,
    UserUpdate,
    UserUpdateMe,
)

router = APIRouter(prefix='/users')


@router.get(
    '/me',
    response_model=UserShortInfo,
    summary="Retrieve current user's data",
)
async def get_user_me(
    current_user: CurrentUserDep,
) -> UserShortInfo:
    """Retrieve data about the current user."""
    return current_user


@router.patch(
    '/me',
    response_model=UserShortInfo,
    summary="Update current user's data",
)
async def patch_user_me(
    current_user: CurrentUserDep,
    user_data: UserUpdateMe,
    session: SessionDep,
) -> UserShortInfo:
    """Update current user data."""
    # Checking the uniqueness of each field
    if user_data.username:
        await validate_unique_username(
            session=session,
            username=user_data.username,
            current_username=current_user.username,
            user_id=current_user.id,
        )

    if user_data.email:
        await validate_unique_email(
            session=session,
            email=user_data.email,
            current_email=current_user.email,
            user_id=current_user.id,
        )

    if user_data.phone:
        await validate_unique_phone(
            session=session,
            phone=user_data.phone,
            current_phone=current_user.phone,
            user_id=current_user.id,
        )

    updated_user = await user_crud.update(
        db_obj=current_user,
        obj_in=user_data,
        session=session,
    )
    await session.commit()

    return updated_user


@router.get(
    '/',
    response_model=list[UserShortInfo],
)
async def get_users(
    session: SessionDep,
    user: CurrentUserDep,
    show_active: bool | None = Query(
        default=None,
        description='Retrieve users based on the `is_active` argument.',
    ),
) -> Sequence[UserShortInfo]:
    """Return data about all users.

    show_active:
        Filter by user activity status

    - True - show only active ones
    - False - show only inactive ones
    - None - show all

    Access: `ADMIN`/`MANAGER`

    """
    validate_current_manager_or_admin(user)
    return await user_crud.get_all(session=session, is_active=show_active)


@router.post(
    '/',
    response_model=UserInfo,
    status_code=status.HTTP_201_CREATED,
    summary='User registration by admin or manager',
)
async def register_user_by_admin_or_manager(
    user: CurrentUserDep,
    user_data: UserCreate,
    session: SessionDep,
) -> UserInfo:
    """Create new user."""
    current_user = validate_current_manager_or_admin(user)
    # Check for MANAGER: can only create USER
    if current_user.role == UserRole.MANAGER and user_data.role != UserRole.USER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='A manager can only create users.',
        )

    await validate_unique_username(
        session=session,
        username=user_data.username,
        current_username=None,
        user_id=None,
    )

    if user_data.email:
        await validate_unique_email(
            session=session,
            email=user_data.email,
            current_email=None,
            user_id=None,
        )

    if user_data.phone:
        await validate_unique_phone(
            session=session,
            phone=user_data.phone,
            current_phone=None,
            user_id=None,
        )

    # check for the presence of at least one contact field (email or phone)
    if not user_data.email and not user_data.phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='An email address or phone number must be provided.',
        )

    new_user = await user_crud.create_user(
        obj_in=UserCreate(
            username=user_data.username,
            email=user_data.email,
            phone=user_data.phone,
            password=user_data.password,
            role=user_data.role,
            is_active=user_data.is_active,
        ),
        session=session,
    )
    await session.commit()

    return new_user


@router.get(
    '/{user_id}',
)
async def get_user_by_id(
    user_id: int,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> UserInfo | UserShortInfo:
    """Get a user by ID."""
    validate_current_manager_or_admin(current_user)
    user = await user_crud.get(obj_id=user_id, session=session)

    if not user:
        log(logging.INFO, f'User with id={user_id} not found', actor=current_user)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='User not found',
        )

    if current_user.role == UserRole.ADMIN:
        return UserInfo.model_validate(user)
    return UserShortInfo.model_validate(user)


@router.patch(
    '/{user_id}',
    response_model=UserInfo,
)
async def update_user_by_id(
    user_id: int,
    user_data: UserUpdate,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> UserInfo:
    """Update user by ID.

    Access: `ADMIN`/`MANAGER`
    """
    validate_current_manager_or_admin(current_user)
    user_to_update = await user_crud.get(obj_id=user_id, session=session)

    if not user_to_update:
        log(logging.INFO, f'User with id={user_id} not found', actor=current_user)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='User not found',
        )

    # restrictions for the manager
    if current_user.role == UserRole.MANAGER and (
        user_to_update.role != UserRole.USER or any([user_data.role, user_data.is_active])
    ):
        log(
            logging.INFO,
            f'User {current_user.username} does not have sufficient permissions to modify '
            f'the user {user_to_update.username} with data: {user_data.model_dump()}',
            actor=current_user,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Insufficient permissions to modify this data.',
        )

    # Check: prevent changing another administrator's role
    if user_data.role is not None and user_to_update.role == UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='The administrator role cannot be changed.',
        )

    # Check: cannot deactivate oneself
    if user_data.is_active is False and user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='You cannot deactivate yourself.',
        )

    if user_data.username:
        await validate_unique_username(
            session=session,
            username=user_data.username,
            current_username=user_to_update.username,
            user_id=user_id,
        )

    if user_data.email:
        await validate_unique_email(
            session=session,
            email=user_data.email,
            current_email=user_to_update.email,
            user_id=user_id,
        )

    if user_data.phone:
        await validate_unique_phone(
            session=session,
            phone=user_data.phone,
            current_phone=user_to_update.phone,
            user_id=user_id,
        )

    updated_user = user_crud.update(
        db_obj=user_to_update,
        obj_in=user_data,
        session=session,
    )
    await session.commit()

    return await updated_user


@router.patch(
    '/{user_id}/deactivate',
    response_model=UserInfo,
)
async def deactivate_user_by_id(
    user_id: int,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> UserInfo:
    """Deactivate user. For ADMIN only."""
    validate_current_admin(current_user)
    # cannot deactivate yourself
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='You cannot deactivate yourself.',
        )

    # Retrieve the user for deactivation.
    user_to_deactivate = await user_crud.get(obj_id=user_id, session=session)

    if not user_to_deactivate:
        log(logging.INFO, f'User with id={user_id} not found', actor=current_user)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='User not found',
        )

    # if the user is already deactivated
    if not user_to_deactivate.is_active:
        log(logging.INFO, f'The user with id={user_id} is already deactivated.', actor=current_user)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='The user has already been deactivated.',
        )

    updated_user = await user_crud.update(
        db_obj=user_to_deactivate,
        obj_in=UserDeactivate(is_active=False),
        session=session,
    )
    await session.commit()

    return updated_user


@router.patch(
    '/{user_id}/activate',
    response_model=UserInfo,
)
async def activate_user_by_id(
    user_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> UserInfo:
    """Activate user. For ADMIN only."""
    validate_current_admin(current_user)
    user_to_activate = await user_crud.get(obj_id=user_id, session=session)

    if not user_to_activate:
        log(logging.INFO, f'User with id={user_id} not found', actor=current_user)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='User not found',
        )

    # If the user is already activated
    if user_to_activate.is_active:
        log(logging.INFO, f'The user with id={user_id} is already activated.', actor=current_user)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='The user is already activated.',
        )

    updated_user = await user_crud.update(
        db_obj=user_to_activate,
        obj_in=UserDeactivate(is_active=True),
        session=session,
    )
    await session.commit()

    return updated_user
