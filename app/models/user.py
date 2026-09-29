"""SQLAlchemy models for ``roles`` and ``users``."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Role(Base):
    __tablename__ = "roles"

    role_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    role_name: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    users: Mapped[list["User"]] = relationship(back_populates="role")


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.role_id"), nullable=False)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=True
    )

    role: Mapped["Role"] = relationship(back_populates="users")

    @property
    def role_name(self) -> str | None:
        return self.role.role_name if self.role else None
