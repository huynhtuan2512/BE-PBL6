"""Read-only table status endpoint for staff and administrators."""

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AppException
from app.core.security import require_roles
from app.models.table import Table
from app.schemas.common import SuccessResponse

router = APIRouter(
    prefix="/tables",
    tags=["Tables - Bàn"],
    dependencies=[Depends(require_roles("ADMIN", "STAFF"))],
)
public_router = APIRouter(
    prefix="/public/tables",
    tags=["Public tables - Trạng thái bàn khách hàng"],
)


class TableResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    table_id: str
    table_number: int
    capacity: int | None = None
    status: str | None = None
    created_at: datetime | None = None


@router.get(
    "",
    response_model=SuccessResponse[list[TableResponse]],
    summary="Lấy danh sách bàn cùng trạng thái hiện tại",
)
async def list_tables(db: AsyncSession = Depends(get_db)):
    """Return table identifiers, capacity, and current status from the tables table."""
    result = await db.execute(select(Table).order_by(Table.table_number))
    tables = result.scalars().all()
    return SuccessResponse(data=[TableResponse.model_validate(table) for table in tables])


@router.get(
    "/{table_id}",
    response_model=SuccessResponse[TableResponse],
    summary="Lấy trạng thái hiện tại của một bàn",
)
async def get_table_status(table_id: str, db: AsyncSession = Depends(get_db)):
    table = (
        await db.execute(select(Table).where(Table.table_id == table_id))
    ).scalar_one_or_none()
    if table is None:
        raise AppException(status_code=404, message="Không tìm thấy bàn")
    return SuccessResponse(data=TableResponse.model_validate(table))


@public_router.get(
    "/{table_id}/status",
    response_model=SuccessResponse[TableResponse],
    summary="Tra cứu trạng thái bàn cho giao diện khách hàng",
)
async def get_customer_table_status(table_id: str, db: AsyncSession = Depends(get_db)):
    table = (
        await db.execute(select(Table).where(Table.table_id == table_id))
    ).scalar_one_or_none()
    if table is None:
        raise AppException(status_code=404, message="Mã bàn không hợp lệ hoặc không tồn tại")
    return SuccessResponse(data=TableResponse.model_validate(table))
