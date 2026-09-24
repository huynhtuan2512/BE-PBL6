"""
app/models/node.py
-------------------
Bảng: nodes
Mỗi node đại diện cho 1 điểm mốc vật lý trong nhà hàng, được đánh dấu bằng
1 mã QR dán trên sàn. Robot khi quét được QR sẽ biết mình đang ở node nào.
"""

import enum

from sqlalchemy import Enum, Float, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class NodeType(str, enum.Enum):
    KITCHEN = "KITCHEN"        # Điểm xuất phát / bếp
    TABLE = "TABLE"            # Điểm đặt bàn ăn
    WAYPOINT = "WAYPOINT"      # Điểm trung gian trên đường đi (giao lộ)
    CHARGING = "CHARGING"      # Trạm sạc robot


class Node(Base, TimestampMixin):
    """Bảng nodes: các điểm mốc (gắn QR code) trong sơ đồ nhà hàng."""

    __tablename__ = "nodes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    node_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)  # VD: QR_N01
    node_type: Mapped[NodeType] = mapped_column(Enum(NodeType), nullable=False, default=NodeType.WAYPOINT)

    # Tọa độ tương đối trên sơ đồ 2D của nhà hàng (phục vụ hiển thị bản đồ trên Dashboard)
    pos_x: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    pos_y: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    table: Mapped["Table"] = relationship(back_populates="node", uselist=False)  # noqa: F821
