"""SQLAlchemy models for ``orders`` and ``order_details``."""

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OrderStatus(str, enum.Enum):
    PENDING = "PENDING"
    PREPARING = "PREPARING"
    DELIVERING = "DELIVERING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class Order(Base):
    __tablename__ = "orders"

    order_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    table_id: Mapped[str] = mapped_column(
        ForeignKey("tables.table_id"), nullable=False, index=True
    )
    created_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, index=True
    )
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=True)
    order_status: Mapped[str] = mapped_column(
        String(30), default=OrderStatus.PENDING, nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=True
    )

    table: Mapped["Table"] = relationship()  # noqa: F821
    created_by_user: Mapped["User | None"] = relationship()  # noqa: F821
    order_details: Mapped[list["OrderDetail"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class OrderDetail(Base):
    __tablename__ = "order_details"

    detail_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    order_id: Mapped[str] = mapped_column(
        ForeignKey("orders.order_id", ondelete="CASCADE"), nullable=False, index=True
    )
    dish_id: Mapped[str] = mapped_column(
        ForeignKey("dishes.dish_id"), nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=True)
    served_status: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)

    order: Mapped["Order"] = relationship(back_populates="order_details")
    dish: Mapped["Dish"] = relationship(back_populates="order_details")  # noqa: F821
