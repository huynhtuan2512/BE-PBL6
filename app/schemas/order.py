"""Order schemas matching ``orders`` and ``order_details``."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OrderItemCreate(BaseModel):
    dish_id: str = Field(..., min_length=1, max_length=50)
    quantity: int = Field(..., gt=0)
    notes: str | None = Field(default=None, max_length=255)


class OrderCreate(BaseModel):
    order_id: str | None = Field(default=None, max_length=50)
    table_id: str = Field(..., min_length=1, max_length=50)
    created_by_user_id: str | None = Field(default=None, max_length=50)
    items: list[OrderItemCreate] = Field(..., min_length=1)


class OrderDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    detail_id: str
    order_id: str
    dish_id: str
    quantity: int | None = None
    price_at_time: float
    notes: str | None = None
    served_status: bool | None = None


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    order_id: str
    table_id: str
    created_by_user_id: str | None = None
    order_status: str | None = None
    total_amount: float | None = None
    order_details: list[OrderDetailResponse] = Field(default_factory=list)
    created_at: datetime | None = None


class OrderStatusUpdate(BaseModel):
    order_status: str = Field(..., pattern="^(PENDING|PROCESSING|DELIVERING|COMPLETED|CANCELLED)$")


class OrderDetailServedUpdate(BaseModel):
    served_status: bool
