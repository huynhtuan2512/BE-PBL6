from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings


class DetectionPayload(BaseModel):
    task_id: int = Field(ge=0)
    dish_id: int = Field(ge=0)


class EventPayload(BaseModel):
    event_type: str = Field(min_length=1, max_length=50)
    message: str = Field(min_length=1, max_length=2000)
    severity: Literal["INFO", "WARNING", "ERROR"] = "INFO"


class StatusPayload(BaseModel):
    delivery_status: Literal["NOT_DELIVERED", "WAITING_FOR_DISH", "DELIVERING", "DELIVERED"]
    detail_id: str | None = Field(default=None, min_length=1, max_length=50)
    obstacle_detected: bool = False


class BestImagePayload(BaseModel):
    task_id: int = Field(ge=0)
    content_type: str = Field(min_length=1, max_length=100)
    image_base64: str = Field(
        min_length=1,
        max_length=((settings.ROBOT_MAX_IMAGE_BYTES + 2) // 3) * 4,
    )
    dish_id: int | None = Field(default=None, ge=0)


class CurrentTaskPayload(BaseModel):
    task_id: int = Field(ge=0)
    dish_id: int | None = Field(default=None, ge=0)


class AckPayload(BaseModel):
    command_id: str = Field(min_length=1, max_length=50)
    status: Literal["DONE", "FAILED"]


class RobotCommandCreate(BaseModel):
    command: Literal["STOP", "RETURN_TO_KITCHEN", "RESET_STATUS"]
    payload: dict = Field(default_factory=dict)


class RobotCommandCreated(BaseModel):
    command_id: str
    command: str
    delivered_live: bool


class RobotTaskStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: int
    dish_id: int | None = None
    detail_id: str | None = None
    order_id: str | None = None
    table_number: int | None = None
    task_status: str | None = None


class RobotDeliveryStateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    robot_id: str
    delivery_status: str
    table_number: int | None = None
    order_id: str | None = None
    obstacle_detected: bool
    updated_at: datetime | None = None
    online: bool = False
    tasks: list[RobotTaskStatusResponse] = Field(default_factory=list)


class RobotCommandResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    command_id: str
    robot_id: str
    command: str
    command_status: str
    created_at: datetime | None = None
    completed_at: datetime | None = None
