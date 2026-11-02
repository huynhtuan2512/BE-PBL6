"""SQLAlchemy model for the QR nodes in the restaurant map."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Node(Base):
    __tablename__ = "nodes"

    qr_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    node_name: Mapped[str] = mapped_column(String(100), nullable=False)
    node_type: Mapped[str] = mapped_column(String(30), nullable=False)
    pos_x: Mapped[int] = mapped_column(Integer, default=0, nullable=True)
    pos_y: Mapped[int] = mapped_column(Integer, default=0, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=True
    )

    routings: Mapped[list["Routing"]] = relationship(
        back_populates="node",
        foreign_keys="Routing.qr_id",
    )  # noqa: F821
