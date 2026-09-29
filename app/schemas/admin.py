"""Schemas for administration endpoints using the SQL dump column names."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NodeCreate(BaseModel):
    qr_id: str
    node_name: str
    node_type: str
    pos_x: int = 0
    pos_y: int = 0


class NodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    qr_id: str
    node_name: str
    node_type: str
    pos_x: int
    pos_y: int
    created_at: datetime | None = None


class NodeUpdate(BaseModel):
    node_name: str | None = None
    node_type: str | None = None
    pos_x: int | None = None
    pos_y: int | None = None


class RoutingCreate(BaseModel):
    id: str | None = None
    qr_id: str
    target_table_id: str | None = None
    action: str
    description: str | None = None


class RoutingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    qr_id: str
    target_table_id: str | None = None
    action: str
    description: str | None = None


class RoutingUpdate(RoutingCreate):
    pass


class SwapRoutingTablesRequest(BaseModel):
    table_a_id: str
    table_b_id: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    username: str
    full_name: str
    phone: str | None = None
    role_id: str
    is_active: bool
    role_name: str | None = None
    created_at: datetime | None = None


class SwapTableRequest(BaseModel):
    order_id: str = Field(..., description="Đơn hàng đang cần chuyển sang bàn mới")
    new_table_id: str = Field(..., description="ID bàn mới khách chuyển tới")


class UserCreate(BaseModel):
    user_id: str | None = None
    username: str
    password: str = Field(..., min_length=6)
    full_name: str
    phone: str | None = None
    role_id: str


class UserUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    is_active: bool | None = None
    role_id: str | None = None
