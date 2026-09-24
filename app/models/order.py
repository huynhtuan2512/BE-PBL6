"""
app/models/order.py
--------------------
Bảng: orders, order_details
"""

import enum

from sqlalchemy import Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class OrderStatus(str, enum.Enum):
    PENDING = "PENDING"          # Vừa tạo, chờ bếp xác nhận
    PREPARING = "PREPARING"      # Bếp đang chuẩn bị món
    DELIVERING = "DELIVERING"    # Robot đang giao món tới bàn
    COMPLETED = "COMPLETED"      # Đã giao xong
    CANCELLED = "CANCELLED"      # Đã hủy


class Order(Base, TimestampMixin):
    """Bảng orders: đơn hàng gọi món theo từng bàn."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    table_id: Mapped[int] = mapped_column(ForeignKey("tables.id"), nullable=False, index=True)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.PENDING, index=True)
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)

    table: Mapped["Table"] = relationship()  # noqa: F821
    order_details: Mapped[list["OrderDetail"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class OrderDetail(Base, TimestampMixin):
    """Bảng order_details: chi tiết từng món trong 1 đơn hàng."""

    __tablename__ = "order_details"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)
    dish_id: Mapped[int] = mapped_column(ForeignKey("dishes.id"), nullable=False)

    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)  # snapshot giá tại thời điểm đặt
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)

    order: Mapped["Order"] = relationship(back_populates="order_details")
    dish: Mapped["Dish"] = relationship()  # noqa: F821
