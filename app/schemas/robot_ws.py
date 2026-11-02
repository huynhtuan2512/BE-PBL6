from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings

MAX_IMAGE_BYTES = settings.ROBOT_MAX_IMAGE_BYTES


class Detection(BaseModel):
    label: str = Field(min_length=1, max_length=100)
    confidence: float = Field(ge=0, le=1)
    quantity: int = Field(default=1, ge=1, le=100)


class DetectionPayload(BaseModel):
    task_id: str = Field(min_length=1, max_length=100)
    table_number: Optional[int] = None
    order_id: Optional[str] = None
    detections: list[Detection]


class EventPayload(BaseModel):
    event_type: str = Field(min_length=1, max_length=50)
    message: str = Field(min_length=1, max_length=2000)
    severity: Literal["INFO", "WARNING", "ERROR"] = "INFO"
    metadata: dict = Field(default_factory=dict)


class StatusPayload(BaseModel):
    delivery_status: Literal["NOT_DELIVERED", "WAITING_FOR_DISH", "DELIVERING", "DELIVERED"]
    table_number: Optional[int] = None
    order_id: Optional[str] = None
    battery_percent: Optional[int] = Field(default=None, ge=0, le=100)
    obstacle_detected: bool = False
    metadata: dict = Field(default_factory=dict)


class BestImagePayload(BaseModel):
    task_id: str = Field(min_length=1, max_length=100)
    confidence: float = Field(ge=0, le=1)
    content_type: str = Field(min_length=1, max_length=100)
    image_base64: str = Field(min_length=1, max_length=((MAX_IMAGE_BYTES + 2) // 3) * 4)
    table_number: Optional[int] = None
    detections: list[dict] = Field(default_factory=list)


class CurrentTaskPayload(BaseModel):
    label: Optional[str] = Field(default=None, max_length=100)
    task_id: Optional[str] = Field(default=None, max_length=100)


class AckPayload(BaseModel):
    command_id: str = Field(min_length=1, max_length=50)
    status: Literal["DONE", "FAILED"] = "DONE"
    message: str = Field(default="", max_length=2000)


# ---- API quản trị ----
class RobotCommandCreate(BaseModel):
    command: Literal["STOP", "RETURN_TO_KITCHEN", "RESET_STATUS"]
    payload: dict = Field(default_factory=dict)


class RobotCommandCreated(BaseModel):
    command_id: str
    command: str
    delivered_live: bool


class RobotDeliveryStateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    robot_id: str
    delivery_status: str
    table_number: int | None = None
    order_id: str | None = None
    battery_percent: int | None = None
    obstacle_detected: bool
    updated_at: datetime | None = None
    online: bool = False


class RobotCommandResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    command_id: str
    robot_id: str
    command: str
    command_status: str
    created_at: datetime | None = None
    completed_at: datetime | None = None