"""Atomic table swapping for an order."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppException
from app.models.order import Order, OrderStatus
from app.models.table import Table, TableStatus


class TableService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def swap_table(self, order_id: str, new_table_id: str) -> Order:
        async with self.db.begin_nested() if self.db.in_transaction() else self.db.begin():
            order = (
                await self.db.execute(
                    select(Order).where(Order.order_id == order_id).with_for_update()
                )
            ).scalar_one_or_none()
            if order is None:
                raise AppException(status_code=404, message="Không tìm thấy đơn hàng")
            if order.order_status in (OrderStatus.COMPLETED, OrderStatus.CANCELLED):
                raise AppException(409, "Không thể chuyển bàn cho đơn đã kết thúc")

            new_table = (
                await self.db.execute(
                    select(Table).where(Table.table_id == new_table_id).with_for_update()
                )
            ).scalar_one_or_none()
            if new_table is None:
                raise AppException(status_code=404, message="Không tìm thấy bàn mới")
            if new_table.table_id == order.table_id:
                raise AppException(status_code=400, message="Đơn hàng đang ở bàn này")
            if new_table.status != TableStatus.EMPTY:
                raise AppException(
                    status_code=409,
                    message="Chỉ có thể chuyển đơn sang bàn đang trống",
                )

            old_table = (
                await self.db.execute(
                    select(Table)
                    .where(Table.table_id == order.table_id)
                    .with_for_update()
                )
            ).scalar_one_or_none()
            if old_table is None:
                raise AppException(status_code=404, message="Không tìm thấy bàn hiện tại")

            other_active_order = await self.db.execute(
                select(Order.order_id)
                .where(
                    Order.table_id == old_table.table_id,
                    Order.order_id != order.order_id,
                    Order.order_status.notin_(("COMPLETED", "CANCELLED")),
                )
                .limit(1)
            )
            old_table.status = (
                TableStatus.OCCUPIED
                if other_active_order.scalar_one_or_none() is not None
                else TableStatus.EMPTY
            )
            order.table_id = new_table.table_id
            new_table.status = TableStatus.OCCUPIED

        await self.db.commit()
        result = await self.db.execute(
            select(Order)
            .options(selectinload(Order.order_details))
            .where(Order.order_id == order.order_id)
        )
        return result.scalar_one()
