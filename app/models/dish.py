"""
app/models/dish.py
-------------------
Bảng: dishes
"""

from sqlalchemy import Boolean, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Dish(Base, TimestampMixin):
    """Bảng dishes: danh mục món ăn trong menu, dùng để đối chiếu với AI Detect Dishes."""

    __tablename__ = "dishes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)  # món chính, khai vị, tráng miệng...
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)

    # Nhãn dùng để mô hình AI (Raspberry Pi) nhận diện món ăn qua camera đối chiếu với món trong đơn
    ai_label: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
