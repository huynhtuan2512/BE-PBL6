"""SQLAlchemy model for the ``tables`` table."""

import enum
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TableStatus(str, enum.Enum):
    EMPTY = "EMPTY"
    OCCUPIED = "OCCUPIED"
    RESERVED = "RESERVED"


class Table(Base):
    __tablename__ = "tables"

    table_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    table_number: Mapped[int] = mapped_column(Integer, nullable=False)
    qr_id: Mapped[str] = mapped_column(
        ForeignKey("nodes.qr_id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(20), default=TableStatus.EMPTY, nullable=True)

    node: Mapped["Node"] = relationship(back_populates="table")  # noqa: F821
