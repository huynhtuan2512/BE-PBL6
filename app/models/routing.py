"""SQLAlchemy model for the SQL dump's routing instructions."""

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Routing(Base):
    __tablename__ = "routings"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    qr_id: Mapped[str] = mapped_column(
        ForeignKey("nodes.qr_id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_table_id: Mapped[str | None] = mapped_column(
        ForeignKey("nodes.qr_id", ondelete="CASCADE"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    node: Mapped["Node"] = relationship(
        foreign_keys=[qr_id], back_populates="routings"
    )  # noqa: F821
    target_node: Mapped["Node | None"] = relationship(foreign_keys=[target_table_id])  # noqa: F821
