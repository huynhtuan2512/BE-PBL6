"""
app/services/order_service.py
-------------------------------
Business logic tạo đơn hàng: validate món ăn tồn tại, snapshot đơn giá tại
thời điểm đặt (unit_price), tính tổng tiền, cập nhật trạng thái bàn.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppException
from app.models.dish import Dish
from app.models.order import Order, OrderDetail, OrderStatus
from app.models.table import Table, TableStatus
from app.schemas.order import OrderCreate


class OrderService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_order(self, payload: OrderCreate) -> Order:
        # Kiểm tra bàn tồn tại
        table_result = await self.db.execute(select(Table).where(Table.id == payload.table_id))
        table = table_result.scalar_one_or_none()
        if table is None:
            raise AppException(status_code=404, message="Không tìm thấy bàn")

        order = Order(table_id=table.id, status=OrderStatus.PENDING, note=payload.note, total_amount=0)
        self.db.add(order)
        await self.db.flush()  # để lấy order.id trước khi commit, dùng cho order_details

        total = 0.0
        for item in payload.items:
            dish_result = await self.db.execute(select(Dish).where(Dish.id == item.dish_id))
            dish = dish_result.scalar_one_or_none()
            if dish is None or not dish.is_available:
                raise AppException(status_code=404, message=f"Món ăn id={item.dish_id} không tồn tại hoặc đã hết")

            line_total = float(dish.price) * item.quantity
            total += line_total

            detail = OrderDetail(
                order_id=order.id,
                dish_id=dish.id,
                quantity=item.quantity,
                unit_price=dish.price,  # snapshot giá tại thời điểm đặt món
                note=item.note,
            )
            self.db.add(detail)

        order.total_amount = total
        table.status = TableStatus.OCCUPIED

        await self.db.commit()

        # Load lại kèm order_details để trả về response đầy đủ
        result = await self.db.execute(
            select(Order).options(selectinload(Order.order_details)).where(Order.id == order.id)
        )
        return result.scalar_one()
