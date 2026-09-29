"""
app/models/__init__.py
-----------------------
Import toàn bộ model tại đây để Alembic autogenerate quét được hết metadata,
và để tránh lỗi "relationship chưa được định nghĩa" khi các model tham chiếu chéo nhau.
"""

from app.models.user import Role, User
from app.models.node import Node
from app.models.routing import Routing
from app.models.table import Table, TableStatus
from app.models.dish import Dish
from app.models.order import Order, OrderDetail, OrderStatus
from app.models.robot import RobotStatus, RobotTravelLog, RobotState
