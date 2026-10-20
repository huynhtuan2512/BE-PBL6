"""SQLAlchemy model for menu categories."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Category(Base):
    __tablename__ = "categories"

    category_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    category_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    dishes: Mapped[list["Dish"]] = relationship(back_populates="category")  # noqa: F821
