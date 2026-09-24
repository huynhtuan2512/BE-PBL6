"""
app/schemas/auth.py
--------------------
"""

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=6)


class UserResponse(BaseModel):
    # Pydantic v2: dùng ConfigDict(from_attributes=True) thay cho orm_mode = True
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str
    is_active: bool
    role_id: int
