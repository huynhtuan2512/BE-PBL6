"""
app/schemas/hardware.py
------------------------
Schemas dành riêng cho giao tiếp với phần cứng: ESP32-CAM (robot) và Raspberry Pi (AI).
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# ROBOT ROUTING (ESP32 quét QR -> hỏi backend đường đi tiếp theo)
# ---------------------------------------------------------------------------
class RobotRoutingQuery(BaseModel):
    """Query params ESP32 gửi lên khi vừa quét được 1 mã QR tại node hiện tại."""
    robot_code: str = Field(..., description="Mã định danh robot, VD: ROBOT_01")
    current_node_code: str = Field(..., description="Mã QR robot vừa quét được")
    target_table_number: str | None = Field(
        default=None, description="Bàn đích cần giao món (bắt buộc nếu đây là lượt đi mới)"
    )
    direction: str = Field(
        default="OUTBOUND", description="OUTBOUND: đang đi giao món | INBOUND: đang quay về bếp"
    )


class RouteStep(BaseModel):
    node_code: str
    action: str  # STRAIGHT | LEFT | RIGHT | STOP


class RobotRoutingResponse(BaseModel):
    robot_code: str
    direction: str
    from_node_code: str
    to_node_code: str
    total_steps: int
    steps: list[RouteStep]
    is_final_node: bool = False


# ---------------------------------------------------------------------------
# ROBOT STATUS HEARTBEAT
# ---------------------------------------------------------------------------
class RobotStatusUpdate(BaseModel):
    robot_code: str
    battery_level: float = Field(..., ge=0, le=100)
    state: str
    current_node_code: str | None = None


class RobotStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    robot_code: str
    battery_level: float
    state: str
    last_heartbeat: datetime | None = None


# ---------------------------------------------------------------------------
# AI DETECTION (Raspberry Pi)
# ---------------------------------------------------------------------------
class AIDetectDishRequest(BaseModel):
    robot_code: str
    order_id: int
    detected_labels: list[str] = Field(..., description="Danh sách nhãn món ăn AI nhận diện được qua camera")


class AIDetectHumanRequest(BaseModel):
    robot_code: str
    node_code: str
    person_detected: bool
    confidence: float = Field(..., ge=0, le=1)
