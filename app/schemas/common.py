"""
app/schemas/common.py
----------------------
Các schema dùng chung toàn hệ thống.
"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    """Response format chuẩn cho các API trả dữ liệu thành công."""
    status: str = "success"
    data: T | None = None
    message: str | None = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
