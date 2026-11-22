from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, LargeBinary, String, Text, func
from sqlalchemy.dialects.mysql import LONGBLOB, LONGTEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

_LongText = Text().with_variant(LONGTEXT(), "mysql", "mariadb")
_LongBlob = LargeBinary().with_variant(LONGBLOB(), "mysql", "mariadb")


class RobotTask(Base):
    __tablename__ = "robot_tasks"

    robot_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    task_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    dish_id: Mapped[int | None] = mapped_column(ForeignKey("dishes.dish_id"), nullable=True)
    detail_id: Mapped[str | None] = mapped_column(
        ForeignKey("order_details.detail_id", ondelete="SET NULL"), unique=True, nullable=True
    )
    order_id: Mapped[str | None] = mapped_column(
        ForeignKey("orders.order_id", ondelete="SET NULL"), nullable=True
    )
    table_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    task_status: Mapped[str | None] = mapped_column(String(30), default="WAITING_FOR_DISH")
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class RobotDetection(Base):
    __tablename__ = "robot_detections"

    detection_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    robot_id: Mapped[str] = mapped_column(String(50), nullable=False)
    task_id: Mapped[int] = mapped_column(Integer, nullable=False)
    dish_id: Mapped[int] = mapped_column(ForeignKey("dishes.dish_id"), nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class RobotBestImage(Base):
    __tablename__ = "robot_best_images"

    image_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    robot_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    task_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dish_id: Mapped[int | None] = mapped_column(ForeignKey("dishes.dish_id"), nullable=True)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    image_data: Mapped[bytes] = mapped_column(_LongBlob, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class RobotEvent(Base):
    __tablename__ = "robot_events"

    event_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    robot_id: Mapped[str] = mapped_column(String(50), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(10), nullable=False, default="INFO")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class RobotDeliveryState(Base):
    __tablename__ = "robot_state"

    robot_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    delivery_status: Mapped[str] = mapped_column(String(30), nullable=False, default="NOT_DELIVERED")
    table_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    order_id: Mapped[str | None] = mapped_column(
        ForeignKey("orders.order_id", ondelete="SET NULL"), nullable=True
    )
    obstacle_detected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class RobotCommand(Base):
    __tablename__ = "robot_commands"

    command_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    robot_id: Mapped[str] = mapped_column(String(50), nullable=False)
    command: Mapped[str] = mapped_column(String(30), nullable=False)
    payload_json: Mapped[str | None] = mapped_column(_LongText, nullable=True)
    command_status: Mapped[str] = mapped_column(String(10), nullable=False, default="PENDING")
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
