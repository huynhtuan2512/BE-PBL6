"""
app/schemas/order.py
---------------------
"""

from pydantic import BaseModel, ConfigDict, Field


class OrderItemCreate(BaseModel):
    dish_id: int
    quantity: int = Field(..., gt=0)
    note: str | None = None


class OrderCreate(BaseModel):
    table_id: int
    items: list[OrderItemCreate] = Field(..., min_length=1)
    note: str | None = None


class OrderDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dish_id: int
    quantity: int
    unit_price: float
    note: str | None = None


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    table_id: int
    status: str
    total_amount: float
    order_details: list[OrderDetailResponse] = []


class OrderStatusUpdate(BaseModel):
    status: str
