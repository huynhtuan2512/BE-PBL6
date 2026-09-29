"""Atomic table swapping for an order."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.models.order import Order
from app.models.table import Table, TableStatus


class TableService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def swap_table(self, order_id: str, new_table_id: str) -> Order:
        async with self.db.begin_nested() if self.db.in_transaction() else self.db.begin():
            order = (
                await self.db.execute(select(Order).where(Order.order_id == order_id))
            ).scalar_one_or_none()
            if order is None:
                raise AppException(status_code=404, message="Không tìm thấy đơn hàng")

            new_table = (
                await self.db.execute(select(Table).where(Table.table_id == new_table_id))
            ).scalar_one_or_none()
            if new_table is None:
                raise AppException(status_code=404, message="Không tìm thấy bàn mới")
            if new_table.status == TableStatus.OCCUPIED:
                raise AppException(
                    status_code=400,
                    message="Bàn mới hiện đang có khách, không thể chuyển tới",
                )

            old_table = (
                await self.db.execute(select(Table).where(Table.table_id == order.table_id))
            ).scalar_one_or_none()
            if old_table is not None:
                old_table.status = TableStatus.EMPTY

            order.table_id = new_table.table_id
            new_table.status = TableStatus.OCCUPIED

        await self.db.commit()
        await self.db.refresh(order)
        return order
