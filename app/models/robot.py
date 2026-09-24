"""
app/models/robot.py
--------------------
Bảng: robot_status, robot_travel_logs
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class RobotState(str, enum.Enum):
    IDLE = "IDLE"
    MOVING = "MOVING"
    DELIVERING = "DELIVERING"
    RETURNING = "RETURNING"
    CHARGING = "CHARGING"
    ERROR = "ERROR"


class RobotStatus(Base, TimestampMixin):
    """
    Bảng robot_status: trạng thái realtime của từng robot (đồng bộ 2 chiều với ThingsBoard).
    """

    __tablename__ = "robot_status"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    robot_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)

    battery_level: Mapped[float] = mapped_column(Float, default=100.0)
    state: Mapped[RobotState] = mapped_column(Enum(RobotState), default=RobotState.IDLE)

    current_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id"), nullable=True)
    current_order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), nullable=True)

    last_heartbeat: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    current_node: Mapped["Node"] = relationship()  # noqa: F821


class TravelLogStatus(str, enum.Enum):
    IN_PROGRESS = "IN_PROGRESS"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class RobotTravelLog(Base, TimestampMixin):
    """
    Bảng robot_travel_logs: lịch sử mỗi chuyến đi của robot (lượt đi giao món + lượt về).
    Phục vụ thống kê, truy vết sự cố và tính hiệu năng vận hành.
    """

    __tablename__ = "robot_travel_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    robot_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), nullable=True)

    start_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id"), nullable=False)
    end_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id"), nullable=False)

    direction: Mapped[str] = mapped_column(String(20), nullable=False)  # OUTBOUND (đi) | INBOUND (về)
    path_taken: Mapped[list] = mapped_column(JSON, nullable=False)  # snapshot các bước đã đi thực tế

    status: Mapped[TravelLogStatus] = mapped_column(Enum(TravelLogStatus), default=TravelLogStatus.IN_PROGRESS)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
