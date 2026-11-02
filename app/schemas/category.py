"""Category request and response schemas."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CategoryCreate(BaseModel):
    category_id: str | None = Field(default=None, max_length=50)
    category_name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)

    @field_validator("category_name")
    @classmethod
    def strip_category_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Tên danh mục không được để trống")
        return value


class CategoryUpdate(BaseModel):
    category_name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)

    @field_validator("category_name")
    @classmethod
    def validate_category_name(cls, value: str | None) -> str:
        if value is None or not value.strip():
            raise ValueError("Tên danh mục không được để trống")
        return value.strip()


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category_id: str
    category_name: str
    description: str | None = None
