"""Dish schemas matching ``dishes`` in restaurant.sql."""

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DishCreate(BaseModel):
    dish_id: str | None = Field(default=None, max_length=50)
    category_id: str = Field(..., min_length=1, max_length=50)
    dish_name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    price: float = Field(..., gt=0)
    image_url: str | None = Field(default=None, max_length=255)
    ai_label_id: str | None = Field(default=None, max_length=50)
    is_available: bool = True

    @field_validator("dish_name")
    @classmethod
    def strip_dish_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Tên món ăn không được để trống")
        return value


class DishUpdate(BaseModel):
    category_id: str | None = Field(default=None, min_length=1, max_length=50)
    dish_name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    price: float | None = Field(default=None, gt=0)
    image_url: str | None = Field(default=None, max_length=255)
    ai_label_id: str | None = Field(default=None, max_length=50)
    is_available: bool | None = None

    @field_validator("dish_name")
    @classmethod
    def strip_dish_name(cls, value: str | None) -> str:
        if value is None or not value.strip():
            raise ValueError("Tên món ăn không được để trống")
        return value.strip()

    @model_validator(mode="after")
    def reject_null_required_values(self):
        for field in ("category_id", "dish_name", "price", "is_available"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} không được để trống")
        return self


class DishStatusUpdate(BaseModel):
    is_available: bool


class DishResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    dish_id: str
    category_id: str
    dish_name: str
    description: str | None = None
    price: float
    image_url: str | None = None
    ai_label_id: str | None = None
    is_available: bool | None = None
