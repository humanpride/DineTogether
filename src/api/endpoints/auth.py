import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from core.constants import UserRole
from core.dependencies import CurrentUserDep, SessionDep
from core.logging import log
from core.security import (
    create_access_token,
    get_password_hash,
    verify_password,
)
from core.validators import (
    validate_unique_email,
    validate_unique_phone,
    validate_unique_username,
)
from crud.user import user_crud
from schemas.token import Token
from schemas.user import (
    UserChangePassword,
    UserCreate,
    UserLogin,
    UserRegister,
    UserShortInfo,
    UserUpdateDBPassword,
    login_field_data,
)

router = APIRouter(prefix='/auth')


@router.post(
    '/register',
    response_model=UserShortInfo,
    status_code=status.HTTP_201_CREATED,
    summary='User registration',
)
async def register_user(
    user_data: UserRegister,
    session: SessionDep,
) -> UserShortInfo:
    """Create new account."""
    # Checking the uniqueness of each field
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
        UserCreate(
            username=user_data.username,
            email=user_data.email,
            phone=user_data.phone,
            telegram_id=user_data.telegram_id,
            password=user_data.password,
            role=UserRole.USER,
            is_active=True,
        ),
        session=session,
    )
    await session.commit()

    return new_user


@router.post(
    '/login',
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary='User authentication',
)
async def auth_user(
    user_data: UserLogin,
    session: SessionDep,
) -> Token:
    """Authenticate user with `email` or `phone`."""
    # Search for a user by email or phone number
    try:
        login = await login_field_data(user_data.login)
    except ValueError as error:
        log(logging.WARNING, f'Login validation error: {error}')
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail='Invalid email/phone number',
        )
    user = await user_crud.get_one_or_none(session, **login)

    # Checking for user existence and password match
    if not user or not verify_password(user_data.password, user.hashed_password):
        log(logging.WARNING, f'Failed login attempt for login: {user_data.login}')
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail='Invalid email/phone number or password',
            headers={'WWW-Authenticate': 'Bearer'},
        )

    if not user.is_active:
        log(logging.WARNING, f'Attempt to log in to a deactivated account: {user_data.login}')
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Account deactivated',
        )

    # Creating JWT tokens
    token_data = {'sub': str(user.id), 'role': user.role.value}
    access_token = create_access_token(data=token_data)
    log(logging.INFO, f'User {user.username} has been successfully authenticated.')
    return Token(
        access_token=access_token,
        token_type='bearer',
    )


@router.post('/token', response_model=Token, include_in_schema=False)
async def auth_user_form(
    session: SessionDep,
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Token:
    """Endpoint for OAuth2."""
    # Search for a user by email or phone number
    try:
        login = await login_field_data(form_data.username)
    except ValueError as error:
        log(logging.WARNING, f'Login validation error: {error}')
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail='Invalid email/phone number',
        )
    log(logging.DEBUG, f'The login is - {login}')
    log(logging.DEBUG, f'Searching for user with credentials: {login}')
    user = await user_crud.get_one_or_none(session, **login)
    if not user:
        log(logging.WARNING, f'User not found for login: {form_data.username}')
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail='Invalid email/phone number or password',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    log(logging.DEBUG, 'User found, checking password...')

    if not verify_password(form_data.password, user.hashed_password):
        log(logging.WARNING, f'Failed login attempt for: {form_data.username}')
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail='Invalid email/phone number or password',
            headers={'WWW-Authenticate': 'Bearer'},
        )

    # Creating JWT tokens
    token_data = {'sub': str(user.id), 'role': user.role.value}
    access_token = create_access_token(data=token_data)
    log(logging.INFO, f'User {user.username} has been successfully authenticated')
    return Token(
        access_token=access_token,
        token_type='bearer',
    )


@router.post(
    '/change-password',
    status_code=status.HTTP_200_OK,
    summary='Change current user password',
)
async def change_password(
    password_data: UserChangePassword,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> dict:
    """Change user password."""
    # verify old password
    if not verify_password(password_data.old_password, current_user.hashed_password):
        log(
            logging.WARNING,
            'Incorrect old password entered.',
            actor=current_user.username,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail='Incorrect old password',
        )

    # compare the old and new passwords
    if verify_password(password_data.new_password, current_user.hashed_password):
        log(
            logging.WARNING,
            'New password is the same as the old one.',
            actor=current_user.username,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail='The new password must be different from the old one.',
        )

    # creating an object for update
    user_update = UserUpdateDBPassword(
        hashed_password=get_password_hash(password_data.new_password),
    )

    await user_crud.update(
        db_obj=current_user,
        obj_in=user_update,
        session=session,
    )
    await session.commit()
    log(
        logging.INFO,
        'User has successfully changed their password.',
        actor=current_user.username,
    )
    return {
        'message': 'Password successfully changed.',
    }
