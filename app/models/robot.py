"""SQLAlchemy models for robot status and travel logs."""

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RobotState(str, enum.Enum):
    IDLE = "IDLE"
    MOVING = "MOVING"
    DELIVERING = "DELIVERING"
    RETURNING = "RETURNING"
    CHARGING = "CHARGING"
    ERROR = "ERROR"


class RobotStatus(Base):
    __tablename__ = "robot_status"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    current_qr_id: Mapped[str | None] = mapped_column(
        ForeignKey("nodes.qr_id"), nullable=True, index=True
    )
    current_order_id: Mapped[str | None] = mapped_column(
        ForeignKey("orders.order_id", ondelete="SET NULL"), nullable=True, index=True
    )
    robot_state: Mapped[str] = mapped_column(
        String(30), default=RobotState.IDLE, nullable=True
    )
    obstacle_detected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=True
    )

    current_node: Mapped["Node | None"] = relationship()  # noqa: F821


class RobotTravelLog(Base):
    __tablename__ = "robot_travel_logs"

    log_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    order_id: Mapped[str] = mapped_column(
        ForeignKey("orders.order_id", ondelete="CASCADE"), nullable=False, index=True
    )
    qr_id: Mapped[str] = mapped_column(
        ForeignKey("nodes.qr_id"), nullable=False, index=True
    )
    action_taken: Mapped[str] = mapped_column(String(30), nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=True
    )

    order: Mapped["Order"] = relationship()  # noqa: F821
    node: Mapped["Node"] = relationship()  # noqa: F821
