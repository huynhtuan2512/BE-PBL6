"""
app/models/__init__.py
-----------------------
Import toàn bộ model tại đây để Alembic autogenerate quét được hết metadata,
và để tránh lỗi "relationship chưa được định nghĩa" khi các model tham chiếu chéo nhau.
"""

from app.models.user import Role, User             # noqa: F401
from app.models.node import Node, NodeType          # noqa: F401
from app.models.routing import Routing              # noqa: F401
from app.models.table import Table, TableStatus     # noqa: F401
from app.models.dish import Dish                    # noqa: F401
from app.models.order import Order, OrderDetail, OrderStatus  # noqa: F401
from app.models.robot import RobotStatus, RobotTravelLog, RobotState, TravelLogStatus  # noqa: F401
