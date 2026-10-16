import uuid

from fastapi import Request
from fastapi.responses import ORJSONResponse

from app.core.exceptions import AppException
from app.core.logger import get_logger


logger = get_logger("exception_handler")


async def app_exception_handler(
    request: Request,
    exc: AppException,
):
    request_id = str(uuid.uuid4())

    logger.error(
        "application_exception",
        request_id=request_id,
        path=request.url.path,
        method=request.method,
        error_code=exc.error_code,
        error_message=exc.message,
    )

    return ORJSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
            },
            "request_id": request_id,
        },
    )

async def unexpected_exception_handler(
    request: Request,
    exc: Exception,
):
    request_id = str(uuid.uuid4())

    logger.exception(
        "unexpected_exception",
        request_id=request_id,
        path=request.url.path,
        method=request.method,
    )

    return ORJSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred.",
            },
            "request_id": request_id,
        },
    )