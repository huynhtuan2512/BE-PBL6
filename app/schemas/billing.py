"""Invoice and audit log API schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class InvoiceCreate(BaseModel):
    order_id: str = Field(..., min_length=1, max_length=50)
    discount_amount: float = Field(default=0, ge=0)
    payment_method: Literal["CASH", "BANK_TRANSFER", "CREDIT_CARD", "MOMO"] = "CASH"


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    invoice_id: str
    order_id: str
    user_id: str | None = None
    total_amount: float
    discount_amount: float | None = None
    final_amount: float
    payment_method: str | None = None
    payment_status: str | None = None
    created_at: datetime | None = None


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    log_id: str
    user_id: str | None = None
    action: str
    table_name: str
    description: str | None = None
    created_at: datetime | None = None


class SalesReportRow(BaseModel):
    invoice_id: str
    order_id: str
    table_id: str
    user_id: str | None = None
    staff_name: str | None = None
    total_amount: float
    discount_amount: float | None = None
    final_amount: float
    payment_method: str | None = None
    payment_status: str | None = None
    created_at: datetime | None = None


class SalesReportResponse(BaseModel):
    invoice_count: int
    paid_count: int
    refunded_count: int
    unpaid_count: int
    revenue: float
    discount_total: float
    rows: list[SalesReportRow]


class ReportStaffResponse(BaseModel):
    user_id: str
    full_name: str
    role_name: str
