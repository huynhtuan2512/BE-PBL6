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
from app.schemas.order import OrderCreate, OrderDispatchRequest, OrderResponse, OrderStatusUpdate
from app.models.robot import RobotStatus, RobotState
from app.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["Orders - Đơn hàng"])
staff_router = APIRouter(prefix="/staff/orders", tags=["Staff - Đơn hàng"])

staff_or_admin = Depends(require_roles("ADMIN", "STAFF"))


@router.post("", response_model=SuccessResponse[OrderResponse])
async def create_order(payload: OrderCreate, db: AsyncSession = Depends(get_db)):
    service = OrderService(db)
    order = await service.create_order(payload)
    return SuccessResponse(data=OrderResponse.model_validate(order), message="Tạo đơn hàng thành công")


@router.get("", response_model=SuccessResponse[list[OrderResponse]], dependencies=[staff_or_admin])
async def list_orders(status: str | None = None, db: AsyncSession = Depends(get_db)):
    query = select(Order).options(selectinload(Order.order_details)).order_by(Order.order_id.desc())
    if status:
        try:
            query = query.where(Order.order_status == OrderStatus(status))
        except ValueError as exc:
            raise AppException(400, f"Trạng thái không hợp lệ: {status}") from exc
    orders = (await db.execute(query)).scalars().unique().all()
    return SuccessResponse(data=[OrderResponse.model_validate(order) for order in orders])


@router.get("/{order_id}", response_model=SuccessResponse[OrderResponse])
async def get_order(order_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Order).options(selectinload(Order.order_details)).where(Order.order_id == order_id)
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise AppException(status_code=404, message="Không tìm thấy đơn hàng")
    return SuccessResponse(data=OrderResponse.model_validate(order))


@staff_router.patch("/{order_id}/status", response_model=SuccessResponse[OrderResponse], dependencies=[staff_or_admin])
async def update_order_status(order_id: str, payload: OrderStatusUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Order).options(selectinload(Order.order_details)).where(Order.order_id == order_id)
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise AppException(status_code=404, message="Không tìm thấy đơn hàng")

    try:
        order.order_status = OrderStatus(payload.order_status)
    except ValueError as exc:
        raise AppException(status_code=400, message=f"Trạng thái không hợp lệ: {payload.order_status}") from exc

    await db.commit()
    await db.refresh(order)
    return SuccessResponse(data=OrderResponse.model_validate(order), message="Cập nhật trạng thái đơn hàng thành công")


@staff_router.post("/{order_id}/dispatch", response_model=SuccessResponse[OrderResponse], dependencies=[staff_or_admin])
async def dispatch_order(order_id: str, payload: OrderDispatchRequest, db: AsyncSession = Depends(get_db)):
    order = (await db.execute(select(Order).options(selectinload(Order.order_details)).where(Order.order_id == order_id))).scalar_one_or_none()
    if order is None:
        raise AppException(404, "Không tìm thấy đơn hàng")
    robot = (await db.execute(select(RobotStatus).where(RobotStatus.id == payload.robot_id))).scalar_one_or_none()
    if robot is None:
        raise AppException(404, "Không tìm thấy robot")
    if robot.robot_state not in (RobotState.IDLE, RobotState.CHARGING):
        raise AppException(409, "Robot hiện không sẵn sàng để giao hàng")
    robot.current_order_id = order.order_id
    robot.robot_state = RobotState.MOVING
    order.order_status = OrderStatus.DELIVERING
    await db.commit()
    await db.refresh(order)
    return SuccessResponse(data=OrderResponse.model_validate(order), message="Đã xuất phát robot giao đơn")
