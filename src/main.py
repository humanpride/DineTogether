import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from api.metadata import tags_metadata
from api.routers import main_router
from core.initial_data import init_default_admin
from core.logging import log, setup_logging
from core.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Жизненный цикл приложения FastAPI."""
    setup_logging()
    log(logging.INFO, 'Приложение запущено')
    await init_default_admin()
    yield
    log(logging.INFO, 'Приложение остановлено')


app = FastAPI(
    title=settings.title,
    version=settings.version,
    description=settings.description,
    openapi_tags=tags_metadata,
    lifespan=lifespan,
)

app.include_router(main_router)


@app.exception_handler(Exception)
async def common_error_handler(_: Request, exc: Exception) -> JSONResponse:
    """Перехватывает все необработанные ошибки."""
    log(logging.CRITICAL, str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            'code': status.HTTP_500_INTERNAL_SERVER_ERROR,
            'message': str(exc),
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    """Перехватывает все HTTPException приложения и форматирует."""
    detail = exc.detail
    if isinstance(detail, dict) and 'message' in detail:
        detail = detail['message']
    elif not isinstance(detail, str):
        detail = str(detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            'code': exc.status_code,
            'message': detail,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Обрабатывает ошибки валидации входящих данных.

    Возвращает понятные пользователю сообщения об ошибках

    вместо стандартного ответа FastAPI/Pydantic.

    """
    log(logging.INFO, str(exc))
    errors = []

    for error in exc.errors():
        if error['type'] == 'json_invalid':
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    'code': status.HTTP_400_BAD_REQUEST,
                    'message': 'Ошибка синтаксиса JSON',
                },
            )

        # error['loc'][1:] - название поля или номер строки, где ошибка
        field = '.'.join(map(str, error['loc'][1:]))

        if error['type'] == 'missing':
            message = f'Не заполнено обязательное поле {field}.'
        else:
            message = f'Некорректное значение поля {field}.'

        errors.append({'field': field, 'message': message})

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            'code': status.HTTP_422_UNPROCESSABLE_CONTENT,
            'message': 'Проверьте правильность заполнения формы.',
            'errors': errors,
        },
    )


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
