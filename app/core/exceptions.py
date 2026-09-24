"""
app/core/exceptions.py
-----------------------
Định nghĩa Exception tùy chỉnh + Global Exception Handlers.
Toàn bộ lỗi trả về FE đều theo format đồng nhất:
    {"status": "error", "message": "...", "detail": ...}
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger("robot_backend")


class AppException(Exception):
    """
    Exception nghiệp vụ dùng chung toàn hệ thống.
    Ví dụ: raise AppException(status_code=404, message="Không tìm thấy bàn")
    """

    def __init__(self, status_code: int, message: str, detail: str | None = None):
        self.status_code = status_code
        self.message = message
        self.detail = detail
        super().__init__(message)


def register_exception_handlers(app: FastAPI) -> None:
    """Đăng ký toàn bộ handler bắt lỗi tập trung tại main.py (lifespan/startup)."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"status": "error", "message": exc.message, "detail": exc.detail},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        # Lỗi validate dữ liệu đầu vào (Pydantic) -> 422
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "status": "error",
                "message": "Dữ liệu đầu vào không hợp lệ",
                "detail": exc.errors(),
            },
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
        logger.exception("Database error: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": "error", "message": "Lỗi cơ sở dữ liệu", "detail": str(exc)},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled error: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": "error", "message": "Lỗi hệ thống không xác định", "detail": str(exc)},
        )
