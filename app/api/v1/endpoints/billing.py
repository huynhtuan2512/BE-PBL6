"""Invoice and audit log endpoints backed by the SQL schema."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.exceptions import AppException
from app.core.security import get_current_user, require_roles
from app.models.billing import AuditLog, Invoice
from app.models.order import Order, OrderDetail, OrderStatus
from app.models.table import Table, TableStatus
from app.models.user import Role, User
from app.schemas.billing import (
    AuditLogResponse,
    InvoiceCreate,
    InvoiceResponse,
    ReportStaffResponse,
    SalesReportResponse,
    SalesReportRow,
)
from app.schemas.common import SuccessResponse

router = APIRouter(tags=["Billing - Hóa đơn"])
staff_or_admin = Depends(require_roles("ADMIN", "STAFF"))


async def _release_table_if_no_active_orders(db: AsyncSession, order: Order) -> bool:
    table = (
        await db.execute(
            select(Table).where(Table.table_id == order.table_id).with_for_update()
        )
    ).scalar_one_or_none()
    if table is None or table.status != TableStatus.OCCUPIED:
        return False

    active_order = await db.execute(
        select(Order.order_id)
        .where(
            Order.table_id == table.table_id,
            Order.order_id != order.order_id,
            Order.order_status.notin_((OrderStatus.COMPLETED, OrderStatus.CANCELLED)),
        )
        .limit(1)
    )
    if active_order.scalar_one_or_none() is not None:
        return False

    table.status = TableStatus.EMPTY
    return True


@router.post(
    "/invoices",
    response_model=SuccessResponse[InvoiceResponse],
    dependencies=[staff_or_admin],
)
async def create_invoice(
    payload: InvoiceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = (
        await db.execute(
            select(Order)
            .options(selectinload(Order.order_details))
            .where(Order.order_id == payload.order_id)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if order is None:
        raise AppException(404, "Không tìm thấy đơn hàng")
    existing = (
        await db.execute(
            select(Invoice)
            .where(Invoice.order_id == order.order_id)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if existing is not None:
        if existing.payment_status == "REFUNDED":
            raise AppException(409, "Hóa đơn đã hoàn tiền, không thể thanh toán lại")
        if existing.payment_status not in ("PAID", "UNPAID"):
            raise AppException(409, "Hóa đơn có trạng thái thanh toán không hợp lệ")

        was_paid = existing.payment_status == "PAID"
        if not was_paid:
            if order.order_status != OrderStatus.DELIVERING:
                raise AppException(409, "Chỉ thanh toán hóa đơn khi đơn đã phục vụ đủ món")
            unserved = await db.execute(
                select(OrderDetail.detail_id)
                .where(
                    OrderDetail.order_id == order.order_id,
                    OrderDetail.served_status.is_not(True),
                )
                .limit(1)
            )
            if unserved.scalar_one_or_none() is not None:
                raise AppException(409, "Chưa thể thanh toán khi còn món chưa phục vụ")
            existing.payment_status = "PAID"
            existing.payment_method = payload.payment_method
            existing.user_id = current_user.user_id
        order_was_incomplete = order.order_status != OrderStatus.COMPLETED
        order.order_status = OrderStatus.COMPLETED
        table_released = await _release_table_if_no_active_orders(db, order)
        if order_was_incomplete or table_released or not was_paid:
            db.add(
                AuditLog(
                    log_id=f"LOG_{uuid4().hex[:12].upper()}",
                    user_id=current_user.user_id,
                    action="UPDATE",
                    table_name="orders",
                    description=(
                        f"Đồng bộ đơn {order.order_id} theo hóa đơn {existing.invoice_id}"
                        + ("; giải phóng bàn " + order.table_id if table_released else "")
                    ),
                )
            )
        try:
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            raise AppException(409, "Không thể đồng bộ trạng thái hóa đơn và đơn hàng") from exc
        await db.refresh(existing)
        message = (
            "Hóa đơn đã thanh toán trước đó; trạng thái đơn hàng và bàn đã được đồng bộ"
            if was_paid
            else "Thanh toán hóa đơn thành công; đơn hàng và bàn đã được đồng bộ"
        )
        return SuccessResponse(data=InvoiceResponse.model_validate(existing), message=message)
    if order.order_status == OrderStatus.CANCELLED:
        raise AppException(409, "Không thể lập hóa đơn cho đơn đã hủy")
    if order.order_status != OrderStatus.DELIVERING:
        raise AppException(409, "Chỉ thanh toán đơn đã phục vụ đủ món")
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
        raise AppException(409, "Chưa thể thanh toán khi còn món chưa phục vụ")

    total = order.total_amount or Decimal("0")
    discount = Decimal(str(payload.discount_amount))
    if discount > total:
        raise AppException(400, "Giảm giá không được lớn hơn tổng đơn hàng")
    invoice = Invoice(
        invoice_id=f"INV_{uuid4().hex[:12].upper()}",
        order_id=order.order_id,
        user_id=current_user.user_id,
        total_amount=total,
        discount_amount=discount,
        final_amount=total - discount,
        payment_method=payload.payment_method,
        payment_status="PAID",
    )
    order.order_status = OrderStatus.COMPLETED
    db.add(invoice)
    await _release_table_if_no_active_orders(db, order)
    db.add(
        AuditLog(
            log_id=f"LOG_{uuid4().hex[:12].upper()}",
            user_id=current_user.user_id,
            action="CREATE",
            table_name="invoices",
            description=f"Tạo hóa đơn {invoice.invoice_id} cho đơn {order.order_id}",
        )
    )
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise AppException(409, "Đơn hàng đã có hóa đơn") from exc
    await db.refresh(invoice)
    return SuccessResponse(data=InvoiceResponse.model_validate(invoice), message="Thanh toán thành công")


@router.get("/invoices", response_model=SuccessResponse[list[InvoiceResponse]], dependencies=[staff_or_admin])
async def list_invoices(
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    invoices = (
        await db.execute(select(Invoice).order_by(Invoice.created_at.desc()).limit(limit))
    ).scalars().all()
    return SuccessResponse(data=[InvoiceResponse.model_validate(invoice) for invoice in invoices])


@router.get(
    "/invoices/{invoice_id}",
    response_model=SuccessResponse[InvoiceResponse],
    dependencies=[staff_or_admin],
)
async def get_invoice(invoice_id: str, db: AsyncSession = Depends(get_db)):
    invoice = (
        await db.execute(select(Invoice).where(Invoice.invoice_id == invoice_id))
    ).scalar_one_or_none()
    if invoice is None:
        raise AppException(404, "Không tìm thấy hóa đơn")
    return SuccessResponse(data=InvoiceResponse.model_validate(invoice))


@router.get(
    "/admin/reports/sales",
    response_model=SuccessResponse[SalesReportResponse],
    dependencies=[Depends(require_roles("ADMIN"))],
)
async def get_sales_report(
    date_from: date | None = None,
    date_to: date | None = None,
    month: int | None = Query(None, ge=1, le=12),
    year: int | None = Query(None, ge=2000, le=2100),
    payment_status: str | None = Query(None, pattern="^(PAID|UNPAID|REFUNDED)$"),
    user_id: str | None = Query(None, max_length=50),
    db: AsyncSession = Depends(get_db),
):
    if (month is None) != (year is None):
        raise AppException(400, "Tháng và năm phải được cung cấp cùng nhau")
    if month is not None and (date_from is not None or date_to is not None):
        raise AppException(400, "Chọn khoảng ngày hoặc tháng/năm, không cả hai")
    if date_from and date_to and date_from > date_to:
        raise AppException(400, "Ngày bắt đầu không được sau ngày kết thúc")

    query = (
        select(Invoice, Order.table_id, User.full_name)
        .join(Order, Order.order_id == Invoice.order_id)
        .outerjoin(User, User.user_id == Invoice.user_id)
        .order_by(Invoice.created_at.desc(), Invoice.invoice_id)
    )
    if date_from:
        query = query.where(Invoice.created_at >= datetime.combine(date_from, time.min))
    if date_to:
        query = query.where(
            Invoice.created_at < datetime.combine(date_to + timedelta(days=1), time.min)
        )
    if month is not None and year is not None:
        month_start = date(year, month, 1)
        next_year = year + 1 if month == 12 else year
        next_month = 1 if month == 12 else month + 1
        month_end = date(next_year, next_month, 1)
        query = query.where(
            Invoice.created_at >= datetime.combine(month_start, time.min),
            Invoice.created_at < datetime.combine(month_end, time.min),
        )
    if payment_status:
        query = query.where(Invoice.payment_status == payment_status)
    if user_id:
        query = query.where(Invoice.user_id == user_id)

    results = (await db.execute(query)).all()
    rows = [
        SalesReportRow(
            invoice_id=invoice.invoice_id,
            order_id=invoice.order_id,
            table_id=table_id,
            user_id=invoice.user_id,
            staff_name=staff_name,
            total_amount=invoice.total_amount,
            discount_amount=invoice.discount_amount,
            final_amount=invoice.final_amount,
            payment_method=invoice.payment_method,
            payment_status=invoice.payment_status,
            created_at=invoice.created_at,
        )
        for invoice, table_id, staff_name in results
    ]
    return SuccessResponse(
        data=SalesReportResponse(
            invoice_count=len(rows),
            paid_count=sum(row.payment_status == "PAID" for row in rows),
            refunded_count=sum(row.payment_status == "REFUNDED" for row in rows),
            unpaid_count=sum(row.payment_status == "UNPAID" for row in rows),
            revenue=sum(
                (Decimal(str(row.final_amount)) for row in rows if row.payment_status == "PAID"),
                Decimal("0"),
            ),
            discount_total=sum(
                (Decimal(str(row.discount_amount or 0)) for row in rows),
                Decimal("0"),
            ),
            rows=rows,
        )
    )


@router.get(
    "/admin/reports/staff",
    response_model=SuccessResponse[list[ReportStaffResponse]],
    dependencies=[Depends(require_roles("ADMIN"))],
)
async def list_report_staff(db: AsyncSession = Depends(get_db)):
    staff = (
        await db.execute(
            select(User.user_id, User.full_name, Role.role_name)
            .join(Role, Role.role_id == User.role_id)
            .where(Role.role_name.in_(("ADMIN", "STAFF")))
            .order_by(User.full_name)
        )
    ).all()
    return SuccessResponse(
        data=[
            ReportStaffResponse(user_id=user_id, full_name=full_name, role_name=role_name)
            for user_id, full_name, role_name in staff
        ]
    )


@router.get(
    "/admin/audit-logs",
    response_model=SuccessResponse[list[AuditLogResponse]],
    dependencies=[Depends(require_roles("ADMIN"))],
)
async def list_audit_logs(
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    logs = (
        await db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit))
    ).scalars().all()
    return SuccessResponse(data=[AuditLogResponse.model_validate(log) for log in logs])
