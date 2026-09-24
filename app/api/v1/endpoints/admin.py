"""
app/api/v1/endpoints/admin.py
--------------------------------
Router quản trị: Users, Nodes, Routings, Swap-tables.
Toàn bộ endpoint yêu cầu quyền ADMIN (trừ khi ghi chú riêng).
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import hash_password, require_roles
from app.models.node import Node
from app.models.order import Order
from app.models.routing import Routing
from app.models.user import User
from app.schemas.admin import (
    NodeCreate,
    NodeResponse,
    RoutingCreate,
    RoutingResponse,
    SwapTableRequest,
    UserCreate,
)
from app.schemas.common import SuccessResponse
from app.schemas.order import OrderResponse
from app.services.table_service import TableService

router = APIRouter(prefix="/admin", tags=["Admin - Quản trị hệ thống"])

# Toàn bộ route trong router này yêu cầu vai trò ADMIN
admin_only = Depends(require_roles("ADMIN"))


# ============================================================================
# USERS
# ============================================================================
@router.post("/users", response_model=SuccessResponse[dict], dependencies=[admin_only])
async def create_user(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role_id=payload.role_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return SuccessResponse(data={"id": user.id, "username": user.username}, message="Tạo tài khoản thành công")


# ============================================================================
# NODES (Sơ đồ định vị QR)
# ============================================================================
@router.post("/nodes", response_model=SuccessResponse[NodeResponse], dependencies=[admin_only])
async def create_node(payload: NodeCreate, db: AsyncSession = Depends(get_db)):
    node = Node(**payload.model_dump())
    db.add(node)
    await db.commit()
    await db.refresh(node)
    return SuccessResponse(data=NodeResponse.model_validate(node), message="Tạo node thành công")


@router.get("/nodes", response_model=SuccessResponse[list[NodeResponse]], dependencies=[admin_only])
async def list_nodes(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Node))
    nodes = result.scalars().all()
    return SuccessResponse(data=[NodeResponse.model_validate(n) for n in nodes])


# ============================================================================
# ROUTINGS (Ma trận đường đi tiền tính toán giữa các node)
# ============================================================================
@router.post("/routings", response_model=SuccessResponse[RoutingResponse], dependencies=[admin_only])
async def create_routing(payload: RoutingCreate, db: AsyncSession = Depends(get_db)):
    """
    Khai báo 1 đường đi tiền tính toán giữa 2 node. path_steps do kỹ thuật viên
    tự nhập tay dựa trên sơ đồ vật lý thực tế của nhà hàng (offline design time),
    hoặc do 1 công cụ BFS/Dijkstra riêng sinh ra rồi import vào đây.
    """
    routing = Routing(**payload.model_dump())
    db.add(routing)
    await db.commit()
    await db.refresh(routing)
    return SuccessResponse(data=RoutingResponse.model_validate(routing), message="Tạo routing thành công")


# ============================================================================
# SWAP TABLE
# ============================================================================
@router.post("/swap-table", response_model=SuccessResponse[OrderResponse], dependencies=[admin_only])
async def swap_table(payload: SwapTableRequest, db: AsyncSession = Depends(get_db)):
    service = TableService(db)
    order = await service.swap_table(order_id=payload.order_id, new_table_id=payload.new_table_id)
    return SuccessResponse(data=OrderResponse.model_validate(order), message="Hoán đổi bàn thành công")
