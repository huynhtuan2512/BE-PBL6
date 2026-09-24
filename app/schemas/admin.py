"""
app/schemas/admin.py
---------------------
Schemas cho các API quản trị: Users, Nodes, Routings, Swap-tables.
"""

from pydantic import BaseModel, ConfigDict, Field


# ---- Node ----
class NodeCreate(BaseModel):
    node_code: str
    node_type: str
    pos_x: float = 0.0
    pos_y: float = 0.0
    description: str | None = None


class NodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    node_code: str
    node_type: str
    pos_x: float
    pos_y: float


# ---- Routing (khai báo cạnh / đường đi tiền tính toán) ----
class RoutingCreate(BaseModel):
    from_node_id: int
    to_node_id: int
    path_steps: list[dict]
    distance: float = 0


class RoutingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    from_node_id: int
    to_node_id: int
    distance: float
    is_active: bool


# ---- Swap tables (hoán đổi bàn khi khách đổi chỗ ngồi) ----
class SwapTableRequest(BaseModel):
    order_id: int = Field(..., description="Đơn hàng đang cần chuyển sang bàn mới")
    new_table_id: int = Field(..., description="ID bàn mới khách chuyển tới")


# ---- User management ----
class UserCreate(BaseModel):
    username: str
    password: str = Field(..., min_length=6)
    full_name: str
    role_id: int


class UserUpdate(BaseModel):
    full_name: str | None = None
    is_active: bool | None = None
    role_id: int | None = None
