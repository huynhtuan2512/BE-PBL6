from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, DateTime, Index, Integer, LargeBinary, Numeric,
    PrimaryKeyConstraint, SmallInteger, String, Text, func,
)
from sqlalchemy.dialects.mysql import LONGBLOB, LONGTEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

_LongText = Text().with_variant(LONGTEXT(), "mysql", "mariadb")
_LongBlob = LargeBinary().with_variant(LONGBLOB(), "mysql", "mariadb")


class RobotDetection(Base):
    __tablename__ = "robot_detections"
    __table_args__ = (
        Index("idx_robot_detection_task", "robot_id", "task_id"),
        Index("idx_robot_detection_label", "label"),
    )
    detection_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    robot_id: Mapped[str] = mapped_column(String(50), nullable=False)
    task_id: Mapped[str] = mapped_column(String(100), nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    table_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class RobotBestImage(Base):
    __tablename__ = "robot_best_images"
    __table_args__ = (PrimaryKeyConstraint("robot_id", "task_id"),)

    image_id: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    robot_id: Mapped[str] = mapped_column(String(50), nullable=False)
    task_id: Mapped[str] = mapped_column(String(100), nullable=False)
    best_confidence: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    table_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    detections_json: Mapped[str | None] = mapped_column(_LongText, nullable=True)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    image_data: Mapped[bytes] = mapped_column(_LongBlob, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class RobotEvent(Base):
    __tablename__ = "robot_events"
    __table_args__ = (Index("idx_robot_events_time", "robot_id", "created_at"),)

    event_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    robot_id: Mapped[str] = mapped_column(String(50), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(10), nullable=False, default="INFO")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[str | None] = mapped_column(_LongText, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class RobotDeliveryState(Base):
    """Bảng robot_state. Đặt tên khác để không đụng enum RobotState có sẵn."""
    __tablename__ = "robot_state"

    robot_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    delivery_status: Mapped[str] = mapped_column(String(30), nullable=False, default="NOT_DELIVERED")
    table_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    order_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    battery_percent: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    obstacle_detected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    metadata_json: Mapped[str | None] = mapped_column(_LongText, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class RobotCommand(Base):
    __tablename__ = "robot_commands"
    __table_args__ = (
        Index("idx_robot_commands_pending", "robot_id", "command_status", "created_at"),
    )

    command_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    robot_id: Mapped[str] = mapped_column(String(50), nullable=False)
    command: Mapped[str] = mapped_column(String(30), nullable=False)
    payload_json: Mapped[str | None] = mapped_column(_LongText, nullable=True)
    command_status: Mapped[str] = mapped_column(String(10), nullable=False, default="PENDING")
    result_json: Mapped[str | None] = mapped_column(_LongText, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)