"""
app/api/v1/endpoints/orders.py
---------------------------------
Tạo đơn hàng, cập nhật trạng thái đơn hàng (STAFF/ADMIN thao tác).
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.exceptions import AppException
from app.core.security import require_roles
from app.models.order import Order, OrderStatus
from app.schemas.common import SuccessResponse
from app.schemas.order import OrderCreate, OrderResponse, OrderStatusUpdate
from app.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["Orders - Đơn hàng"])

staff_or_admin = Depends(require_roles("ADMIN", "STAFF"))


@router.post("", response_model=SuccessResponse[OrderResponse], dependencies=[staff_or_admin])
async def create_order(payload: OrderCreate, db: AsyncSession = Depends(get_db)):
    service = OrderService(db)
    order = await service.create_order(payload)
    return SuccessResponse(data=OrderResponse.model_validate(order), message="Tạo đơn hàng thành công")


@router.get("/{order_id}", response_model=SuccessResponse[OrderResponse], dependencies=[staff_or_admin])
async def get_order(order_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Order).options(selectinload(Order.order_details)).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise AppException(status_code=404, message="Không tìm thấy đơn hàng")
    return SuccessResponse(data=OrderResponse.model_validate(order))


@router.patch("/{order_id}/status", response_model=SuccessResponse[OrderResponse], dependencies=[staff_or_admin])
async def update_order_status(order_id: int, payload: OrderStatusUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Order).options(selectinload(Order.order_details)).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise AppException(status_code=404, message="Không tìm thấy đơn hàng")

    try:
        order.status = OrderStatus(payload.status)
    except ValueError as exc:
        raise AppException(status_code=400, message=f"Trạng thái không hợp lệ: {payload.status}") from exc

    await db.commit()
    await db.refresh(order)
    return SuccessResponse(data=OrderResponse.model_validate(order), message="Cập nhật trạng thái đơn hàng thành công")
