"""Dish schemas matching ``dishes`` in restaurant.sql."""

from pydantic import BaseModel, ConfigDict, Field


class DishCreate(BaseModel):
    dish_id: str | None = None
    dish_name: str
    price: float = Field(..., gt=0)
    image_url: str | None = None
    ai_label_id: str | None = None
    is_available: bool = True


class DishUpdate(BaseModel):
    dish_name: str | None = None
    price: float | None = Field(default=None, gt=0)
    image_url: str | None = None
    ai_label_id: str | None = None
    is_available: bool | None = None


class DishStatusUpdate(BaseModel):
    is_available: bool


class DishResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    dish_id: str
    dish_name: str
    price: float
    image_url: str | None = None
    ai_label_id: str | None = None
    is_available: bool
