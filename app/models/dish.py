"""SQLAlchemy model for the ``dishes`` table."""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.order import OrderDetail


class Dish(Base):
    __tablename__ = "dishes"

    dish_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[str] = mapped_column(
        ForeignKey("categories.category_id"), nullable=False
    )
    dish_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_available: Mapped[bool | None] = mapped_column(Boolean, default=True, nullable=True)

    category: Mapped["Category"] = relationship(back_populates="dishes")  # noqa: F821
    order_details: Mapped[list["OrderDetail"]] = relationship(back_populates="dish")  # noqa: F821
