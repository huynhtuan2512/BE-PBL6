"""SQLAlchemy model for the ``dishes`` table."""

from sqlalchemy import Boolean, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Dish(Base):
    __tablename__ = "dishes"

    dish_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    dish_name: Mapped[str] = mapped_column(String(100), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ai_label_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=True)

    order_details: Mapped[list["OrderDetail"]] = relationship(back_populates="dish")  # noqa: F821
