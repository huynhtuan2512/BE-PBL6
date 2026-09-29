"""Order schemas matching ``orders`` and ``order_details``."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OrderItemCreate(BaseModel):
    dish_id: str
    quantity: int = Field(..., gt=0)


class OrderCreate(BaseModel):
    order_id: str | None = None
    table_id: str
    created_by_user_id: str | None = None
    items: list[OrderItemCreate] = Field(..., min_length=1)


class OrderDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    detail_id: str
    order_id: str
    dish_id: str
    quantity: int
    served_status: bool


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    order_id: str
    table_id: str
    created_by_user_id: str | None = None
    order_status: str
    total_amount: float
    order_details: list[OrderDetailResponse] = []
    created_at: datetime | None = None


class OrderStatusUpdate(BaseModel):
    order_status: str


class OrderDispatchRequest(BaseModel):
    robot_id: str
