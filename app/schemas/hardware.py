"""Schemas for robot and Raspberry Pi endpoints."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RobotRoutingQuery(BaseModel):
    robot_id: str
    current_qr_id: str
    target_table_number: int | None = None
    direction: str = "OUTBOUND"


class RouteStep(BaseModel):
    qr_id: str
    action: str


class RobotRoutingResponse(BaseModel):
    robot_id: str
    direction: str
    from_qr_id: str
    to_qr_id: str
    total_steps: int
    steps: list[RouteStep]
    is_final_node: bool = False


class RobotStatusUpdate(BaseModel):
    id: str
    robot_state: str
    current_qr_id: str | None = None
    obstacle_detected: bool = False


class RobotStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    current_qr_id: str | None = None
    current_order_id: str | None = None
    robot_state: str
    obstacle_detected: bool
    updated_at: datetime | None = None


class AIDetectDishRequest(BaseModel):
    robot_id: str
    order_id: str
    detected_labels: list[str] = Field(..., description="Nhãn món ăn nhận diện được")


class AIDetectHumanRequest(BaseModel):
    robot_id: str
    qr_id: str
    person_detected: bool
    confidence: float = Field(..., ge=0, le=1)
