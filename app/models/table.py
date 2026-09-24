"""
app/models/table.py
--------------------
Bảng: tables
"""

import enum

from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class TableStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    OCCUPIED = "OCCUPIED"
    RESERVED = "RESERVED"


class Table(Base, TimestampMixin):
    """Bảng tables: bàn ăn thực tế, mỗi bàn gắn với 1 node duy nhất trên sơ đồ."""

    __tablename__ = "tables"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    table_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)  # VD: A01
    capacity: Mapped[int] = mapped_column(Integer, default=4)
    status: Mapped[TableStatus] = mapped_column(Enum(TableStatus), default=TableStatus.AVAILABLE)

    node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id"), unique=True, nullable=False)
    node: Mapped["Node"] = relationship(back_populates="table")  # noqa: F821
