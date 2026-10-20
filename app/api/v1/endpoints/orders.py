"""
app/api/v1/endpoints/orders.py
---------------------------------
Tạo đơn hàng, cập nhật trạng thái đơn hàng (STAFF/ADMIN thao tác).
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import String, cast, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.exceptions import AppException
from app.core.security import require_roles
from app.models.billing import Invoice
from app.models.order import Order, OrderDetail, OrderStatus
from app.models.table import Table, TableStatus
from app.schemas.common import SuccessResponse
from app.schemas.order import (
    OrderCreate,
    OrderDetailServedUpdate,
    OrderResponse,
    OrderStatusUpdate,
)
from app.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["Orders - Đơn hàng"])
public_router = APIRouter(prefix="/public/orders", tags=["Public orders - Tra cứu đơn"])
staff_router = APIRouter(prefix="/staff/orders", tags=["Staff - Đơn hàng"])

staff_or_admin = Depends(require_roles("ADMIN", "STAFF"))


@router.post("", response_model=SuccessResponse[OrderResponse])
async def create_order(payload: OrderCreate, db: AsyncSession = Depends(get_db)):
    service = OrderService(db)
    order = await service.create_order(payload)
    return SuccessResponse(data=OrderResponse.model_validate(order), message="Tạo đơn hàng thành công")


@router.get("", response_model=SuccessResponse[list[OrderResponse]], dependencies=[staff_or_admin])
async def list_orders(
    status: str | None = None,
    search: str | None = Query(None, min_length=1, max_length=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(Order).options(selectinload(Order.order_details)).order_by(Order.order_id.desc())
    if status:
        try:
            query = query.where(Order.order_status == OrderStatus(status))
        except ValueError as exc:
            raise AppException(400, f"Trạng thái không hợp lệ: {status}") from exc
    if search:
        term = f"%{search.strip()}%"
        query = query.join(Table, Table.table_id == Order.table_id).where(
            Order.order_id.ilike(term)
            | Order.table_id.ilike(term)
            | cast(Table.table_number, String).ilike(term)
        )
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


@public_router.get(
    "/{order_id}",
    response_model=SuccessResponse[OrderResponse],
    summary="Tra cứu đơn hàng theo mã đơn và mã bàn",
)
async def get_customer_order(
    order_id: str,
    table_id: str = Query(..., min_length=1, max_length=50),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.order_details))
        .where(Order.order_id == order_id, Order.table_id == table_id)
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise AppException(404, "Không tìm thấy đơn hàng tại bàn này")
    return SuccessResponse(data=OrderResponse.model_validate(order))


@staff_router.patch("/{order_id}/status", response_model=SuccessResponse[OrderResponse], dependencies=[staff_or_admin])
async def update_order_status(order_id: str, payload: OrderStatusUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Order).where(Order.order_id == order_id).with_for_update()
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise AppException(status_code=404, message="Không tìm thấy đơn hàng")

    previous_status = order.order_status
    next_status = OrderStatus(payload.order_status)
    try:
        current_status = OrderStatus(order.order_status)
    except (TypeError, ValueError) as exc:
        raise AppException(409, "Đơn hàng đang có trạng thái không hợp lệ") from exc
    allowed_transitions = {
        OrderStatus.PENDING: {OrderStatus.PROCESSING, OrderStatus.CANCELLED},
        OrderStatus.PROCESSING: {OrderStatus.DELIVERING, OrderStatus.CANCELLED},
        OrderStatus.DELIVERING: set(),
        OrderStatus.COMPLETED: set(),
        OrderStatus.CANCELLED: set(),
    }
    if next_status not in allowed_transitions[current_status]:
        raise AppException(
            409,
            f"Không thể chuyển trạng thái đơn từ {order.order_status} sang {next_status}",
        )
    if next_status == OrderStatus.DELIVERING:
        unserved = await db.execute(
            select(OrderDetail.detail_id)
            .where(
                OrderDetail.order_id == order.order_id,
                OrderDetail.served_status.is_not(True),
            )
            .limit(1)
            .with_for_update()
        )
        if unserved.scalar_one_or_none() is not None:
            raise AppException(409, "Chỉ chuyển sang đang giao khi tất cả món đã được phục vụ")
    if next_status == OrderStatus.CANCELLED:
        invoice = await db.execute(
            select(Invoice.invoice_id).where(Invoice.order_id == order.order_id).limit(1)
        )
        if invoice.scalar_one_or_none() is not None:
            raise AppException(409, "Không thể hủy đơn đã có hóa đơn")
        served = await db.execute(
            select(OrderDetail.detail_id)
            .where(OrderDetail.order_id == order.order_id, OrderDetail.served_status.is_(True))
            .limit(1)
        )
        if served.scalar_one_or_none() is not None:
            raise AppException(409, "Không thể hủy đơn đã phục vụ món")

    order.order_status = next_status
    if next_status == OrderStatus.CANCELLED:
        active_orders = await db.execute(
            select(Order.order_id)
            .where(
                Order.table_id == order.table_id,
                Order.order_id != order.order_id,
                Order.order_status.notin_((OrderStatus.COMPLETED, OrderStatus.CANCELLED)),
            )
            .limit(1)
        )
        if active_orders.scalar_one_or_none() is None:
            table = (
                await db.execute(select(Table).where(Table.table_id == order.table_id))
            ).scalar_one_or_none()
            if table is not None and table.status == TableStatus.OCCUPIED:
                table.status = TableStatus.EMPTY

    await db.commit()
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.order_details))
        .where(Order.order_id == order_id)
    )
    order = result.scalar_one()
    return SuccessResponse(
        data=OrderResponse.model_validate(order),
        message=f"Cập nhật trạng thái đơn hàng từ {previous_status} sang {order.order_status} thành công",
    )


@staff_router.patch(
    "/details/{detail_id}/served",
    response_model=SuccessResponse[OrderResponse],
    dependencies=[staff_or_admin],
)
async def update_order_detail_served(
    detail_id: str,
    payload: OrderDetailServedUpdate,
    db: AsyncSession = Depends(get_db),
):
    detail_result = await db.execute(
        select(OrderDetail).where(OrderDetail.detail_id == detail_id)
    )
    detail = detail_result.scalar_one_or_none()
    if detail is None:
        raise AppException(404, "Không tìm thấy món trong đơn hàng")

    order = (
        await db.execute(
            select(Order).where(Order.order_id == detail.order_id).with_for_update()
        )
    ).scalar_one_or_none()
    if order is None:
        raise AppException(404, "Không tìm thấy đơn hàng")
    if order.order_status != OrderStatus.PROCESSING:
        raise AppException(409, "Chỉ cập nhật món đã phục vụ khi đơn đang chế biến")

    detail.served_status = payload.served_status
    if payload.served_status:
        unserved = await db.execute(
            select(OrderDetail.detail_id)
            .where(
                OrderDetail.order_id == order.order_id,
                OrderDetail.detail_id != detail.detail_id,
                OrderDetail.served_status.is_not(True),
            )
            .limit(1)
            .with_for_update()
        )
        if unserved.scalar_one_or_none() is None:
            order.order_status = OrderStatus.DELIVERING

    await db.commit()
    updated_order = (
        await db.execute(
            select(Order)
            .options(selectinload(Order.order_details))
            .where(Order.order_id == order.order_id)
        )
    ).scalar_one()
    message = (
        "Đã phục vụ món; đơn đã sẵn sàng thanh toán"
        if order.order_status == OrderStatus.DELIVERING
        else "Đã cập nhật trạng thái phục vụ món"
    )
    return SuccessResponse(data=OrderResponse.model_validate(updated_order), message=message)
