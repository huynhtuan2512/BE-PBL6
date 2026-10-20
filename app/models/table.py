"""SQLAlchemy model for the ``tables`` table."""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TableStatus(str, enum.Enum):
    EMPTY = "EMPTY"
    OCCUPIED = "OCCUPIED"
    RESERVED = "RESERVED"
    CLEANING = "CLEANING"


class Table(Base):
    __tablename__ = "tables"

    table_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    table_number: Mapped[int] = mapped_column(Integer, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, default=4, nullable=True)
    status: Mapped[str | None] = mapped_column(
        String(20), default=TableStatus.EMPTY, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=True
    )
