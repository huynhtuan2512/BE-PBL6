"""
app/models/routing.py
----------------------
Bảng: routings
Lưu "ma trận định tuyến" đã được tính toán sẵn (precomputed) giữa cặp
(node xuất phát - node đích). Mỗi bản ghi chứa chuỗi bước đi (path_steps)
mà Robot phải thực hiện tuần tự khi di chuyển từ from_node -> to_node.

path_steps là JSON dạng:
[
  {"node_code": "QR_N01", "action": "STRAIGHT"},
  {"node_code": "QR_N02", "action": "LEFT"},
  {"node_code": "QR_N05", "action": "STOP"}
]
"action" gồm: STRAIGHT, LEFT, RIGHT, STOP (robot tự hiểu để rẽ tại node đó).
"""

from sqlalchemy import ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Routing(Base, TimestampMixin):
    """Bảng routings: đường đi tối ưu tiền tính toán giữa 2 node."""

    __tablename__ = "routings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    from_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id"), nullable=False, index=True)
    to_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id"), nullable=False, index=True)

    # Chuỗi bước đi tuần tự (path finding đã tính sẵn bằng BFS/Dijkstra lúc khai báo sơ đồ)
    path_steps: Mapped[list] = mapped_column(JSON, nullable=False)

    distance: Mapped[float] = mapped_column(Integer, nullable=False, default=0)  # đơn vị: cm hoặc số node
    is_active: Mapped[bool] = mapped_column(default=True)

    from_node: Mapped["Node"] = relationship(foreign_keys=[from_node_id])  # noqa: F821
    to_node: Mapped["Node"] = relationship(foreign_keys=[to_node_id])  # noqa: F821
