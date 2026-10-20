"""Schemas for administration endpoints using the SQL dump column names."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    username: str
    full_name: str
    phone: str | None = None
    role_id: str
    is_active: bool | None = None
    role_name: str | None = None
    created_at: datetime | None = None


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role_id: str
    role_name: str
    description: str | None = None


class SwapTableRequest(BaseModel):
    order_id: str = Field(..., max_length=50, description="Đơn hàng đang cần chuyển sang bàn mới")
    new_table_id: str = Field(..., max_length=50, description="ID bàn mới khách chuyển tới")


class UserCreate(BaseModel):
    user_id: str | None = Field(default=None, max_length=50)
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=20)
    role_id: str = Field(..., min_length=1, max_length=50)

    @field_validator("username", "full_name", "role_id")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Giá trị không được để trống")
        return value

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Mật khẩu không được vượt quá 72 byte")
        return value


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=20)
    is_active: bool | None = None
    role_id: str | None = Field(default=None, min_length=1, max_length=50)
    new_password: str | None = Field(default=None, min_length=6)

    @field_validator("new_password")
    @classmethod
    def validate_new_password_length(cls, value: str | None) -> str | None:
        if value is not None and len(value.encode("utf-8")) > 72:
            raise ValueError("Mật khẩu không được vượt quá 72 byte")
        return value

    @model_validator(mode="after")
    def reject_null_required_values(self):
        for field in ("full_name", "role_id"):
            value = getattr(self, field)
            if field in self.model_fields_set and (value is None or not value.strip()):
                raise ValueError(f"{field} không được để trống")
        return self
