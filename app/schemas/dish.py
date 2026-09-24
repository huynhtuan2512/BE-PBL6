"""
app/schemas/dish.py
--------------------
"""

from pydantic import BaseModel, ConfigDict, Field


class DishCreate(BaseModel):
    name: str
    category: str | None = None
    price: float = Field(..., gt=0)
    image_url: str | None = None
    ai_label: str | None = None


class DishUpdate(BaseModel):
    name: str | None = None
    price: float | None = None
    is_available: bool | None = None


class DishResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str | None
    price: float
    image_url: str | None
    is_available: bool
