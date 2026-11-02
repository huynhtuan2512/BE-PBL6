"""Business logic for creating orders against the SQL dump schema."""

from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppException
from app.models.dish import Dish
from app.models.order import Order, OrderDetail, OrderStatus
from app.models.table import Table, TableStatus
from app.schemas.order import OrderCreate


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12].upper()}"


class OrderService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_order(self, payload: OrderCreate) -> Order:
        table = (
            await self.db.execute(select(Table).where(Table.table_id == payload.table_id))
        ).scalar_one_or_none()
        if table is None:
            raise AppException(status_code=404, message="Không tìm thấy bàn")
        if table.status in (TableStatus.RESERVED, TableStatus.CLEANING):
            raise AppException(409, "Bàn đang được giữ chỗ hoặc dọn dẹp")

        order = Order(
            order_id=payload.order_id or _new_id("ORD"),
            table_id=table.table_id,
            created_by_user_id=payload.created_by_user_id,
            order_status=OrderStatus.PENDING,
            total_amount=0,
        )
        self.db.add(order)
        await self.db.flush()

        total = Decimal("0")
        for item in payload.items:
            dish = (
                await self.db.execute(select(Dish).where(Dish.dish_id == item.dish_id))
            ).scalar_one_or_none()
            if dish is None or not dish.is_available:
                raise AppException(
                    status_code=404,
                    message=f"Món ăn id={item.dish_id} không tồn tại hoặc đã hết",
                )

            total += dish.price * item.quantity
            self.db.add(
                OrderDetail(
                    detail_id=_new_id("DTL"),
                    order_id=order.order_id,
                    dish_id=dish.dish_id,
                    quantity=item.quantity,
                    price_at_time=dish.price,
                    notes=item.notes,
                    served_status=False,
                )
            )

        order.total_amount = total
        table.status = TableStatus.OCCUPIED
        await self.db.commit()

        result = await self.db.execute(
            select(Order)
            .options(selectinload(Order.order_details))
            .where(Order.order_id == order.order_id)
        )
        return result.scalar_one()
