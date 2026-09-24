"""
app/services/table_service.py
------------------------------
Xử lý nghiệp vụ hoán đổi bàn (swap-table): khi khách đổi chỗ ngồi giữa chừng,
cần cập nhật lại table_id của order đang phục vụ MÀ KHÔNG được làm mất dữ liệu
hay để hệ thống rơi vào trạng thái nửa vời (order 1 nơi, robot đi 1 nẻo).
=> Bắt buộc thực hiện trong 1 DB Transaction (atomic).
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.models.order import Order
from app.models.table import Table, TableStatus


class TableService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def swap_table(self, order_id: int, new_table_id: int) -> Order:
        """
        Chuyển 1 order đang phục vụ sang bàn mới.
        Toàn bộ thao tác nằm trong transaction: nếu bất kỳ bước nào lỗi,
        rollback toàn bộ để tránh tình trạng bàn cũ đã "trống" nhưng order vẫn trỏ sai.
        """
        async with self.db.begin_nested() if self.db.in_transaction() else self.db.begin():
            # 1) Khóa order hiện tại
            order_result = await self.db.execute(select(Order).where(Order.id == order_id))
            order = order_result.scalar_one_or_none()
            if order is None:
                raise AppException(status_code=404, message="Không tìm thấy đơn hàng")

            # 2) Kiểm tra bàn mới có sẵn sàng không
            new_table_result = await self.db.execute(select(Table).where(Table.id == new_table_id))
            new_table = new_table_result.scalar_one_or_none()
            if new_table is None:
                raise AppException(status_code=404, message="Không tìm thấy bàn mới")
            if new_table.status == TableStatus.OCCUPIED:
                raise AppException(status_code=400, message="Bàn mới hiện đang có khách, không thể chuyển tới")

            # 3) Trả trạng thái bàn cũ về AVAILABLE
            old_table_result = await self.db.execute(select(Table).where(Table.id == order.table_id))
            old_table = old_table_result.scalar_one_or_none()
            if old_table is not None:
                old_table.status = TableStatus.AVAILABLE

            # 4) Gán order sang bàn mới + đánh dấu bàn mới đang OCCUPIED
            order.table_id = new_table.id
            new_table.status = TableStatus.OCCUPIED

        await self.db.commit()
        await self.db.refresh(order)
        return order
