"""Administrative endpoints (paths remain compatible with the deployed API)."""

from uuid import uuid4

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.exceptions import AppException
from app.core.security import hash_password, require_roles
from app.models.node import Node
from app.models.order import Order
from app.models.routing import Routing
from app.models.table import Table
from app.models.user import User
from app.schemas.admin import (
    NodeCreate,
    NodeResponse,
    NodeUpdate,
    RoutingCreate,
    RoutingResponse,
    RoutingUpdate,
    SwapRoutingTablesRequest,
    SwapTableRequest,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from app.schemas.common import SuccessResponse
from app.schemas.order import OrderResponse
from app.services.table_service import TableService

router = APIRouter(prefix="/admin", tags=["Admin - Quản trị hệ thống"])
admin_only = Depends(require_roles("ADMIN"))


@router.post("/users", response_model=SuccessResponse[dict], dependencies=[admin_only])
async def create_user(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    values = payload.model_dump()
    user = User(
        user_id=values.pop("user_id") or f"USER_{uuid4().hex[:12].upper()}",
        password_hash=hash_password(values.pop("password")),
        **values,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return SuccessResponse(
        data={"user_id": user.user_id, "username": user.username},
        message="Tạo tài khoản thành công",
    )


@router.get("/users", response_model=SuccessResponse[dict], dependencies=[admin_only])
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(User)
        .options(selectinload(User.role))
        .order_by(User.user_id.desc())
    )
    if search:
        query = query.where(
            User.username.ilike(f"%{search}%") | User.full_name.ilike(f"%{search}%")
        )
    users = (
        await db.execute(query.offset((page - 1) * page_size).limit(page_size))
    ).scalars().all()
    return SuccessResponse(
        data={
            "items": [UserResponse.model_validate(user) for user in users],
            "page": page,
            "page_size": page_size,
            "total": len(users),
        }
    )


@router.put("/users/{user_id}", response_model=SuccessResponse[UserResponse], dependencies=[admin_only])
async def update_user(user_id: str, payload: UserUpdate, db: AsyncSession = Depends(get_db)):
    user = (
        await db.execute(
            select(User).options(selectinload(User.role)).where(User.user_id == user_id)
        )
    ).scalar_one_or_none()
    if user is None:
        raise AppException(404, "Không tìm thấy tài khoản")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user, attribute_names=["role"])
    return SuccessResponse(data=UserResponse.model_validate(user), message="Cập nhật tài khoản thành công")


@router.delete("/users/{user_id}", response_model=SuccessResponse[None], dependencies=[admin_only])
async def delete_user(user_id: str, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.user_id == user_id))).scalar_one_or_none()
    if user is None:
        raise AppException(404, "Không tìm thấy tài khoản")
    await db.delete(user)
    await db.commit()
    return SuccessResponse(message="Xóa tài khoản thành công")


@router.post("/nodes", response_model=SuccessResponse[NodeResponse], dependencies=[admin_only])
async def create_node(payload: NodeCreate, db: AsyncSession = Depends(get_db)):
    node = Node(**payload.model_dump())
    db.add(node)
    await db.commit()
    await db.refresh(node)
    return SuccessResponse(data=NodeResponse.model_validate(node), message="Tạo node thành công")


@router.get("/nodes", response_model=SuccessResponse[list[NodeResponse]], dependencies=[admin_only])
async def list_nodes(db: AsyncSession = Depends(get_db)):
    nodes = (await db.execute(select(Node))).scalars().all()
    return SuccessResponse(data=[NodeResponse.model_validate(node) for node in nodes])


@router.get("/qr-nodes", response_model=SuccessResponse[list[NodeResponse]], dependencies=[admin_only])
async def list_qr_nodes(db: AsyncSession = Depends(get_db)):
    return await list_nodes(db)


@router.get("/qr-nodes/{qr_id}", response_model=SuccessResponse[dict], dependencies=[admin_only])
async def get_qr_node(qr_id: str, db: AsyncSession = Depends(get_db)):
    node = (await db.execute(select(Node).where(Node.qr_id == qr_id))).scalar_one_or_none()
    if node is None:
        raise AppException(404, "Không tìm thấy nút QR")
    routings = (
        await db.execute(
            select(Routing).where(
                (Routing.qr_id == qr_id) | (Routing.target_table_id == qr_id)
            )
        )
    ).scalars().all()
    return SuccessResponse(
        data={
            "node": NodeResponse.model_validate(node),
            "routings": [RoutingResponse.model_validate(route) for route in routings],
        }
    )


@router.put("/qr-nodes/{qr_id}", response_model=SuccessResponse[NodeResponse], dependencies=[admin_only])
async def update_qr_node(qr_id: str, payload: NodeUpdate, db: AsyncSession = Depends(get_db)):
    node = (await db.execute(select(Node).where(Node.qr_id == qr_id))).scalar_one_or_none()
    if node is None:
        raise AppException(404, "Không tìm thấy nút QR")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(node, field, value)
    await db.commit()
    await db.refresh(node)
    return SuccessResponse(data=NodeResponse.model_validate(node), message="Cập nhật nút QR thành công")


@router.post("/routings", response_model=SuccessResponse[RoutingResponse], dependencies=[admin_only])
async def create_routing(payload: RoutingCreate, db: AsyncSession = Depends(get_db)):
    values = payload.model_dump()
    route = Routing(
        id=values.pop("id") or f"ROUTE_{uuid4().hex[:12].upper()}",
        **values,
    )
    db.add(route)
    await db.commit()
    await db.refresh(route)
    return SuccessResponse(data=RoutingResponse.model_validate(route), message="Tạo routing thành công")


@router.post("/routings/update", response_model=SuccessResponse[RoutingResponse], dependencies=[admin_only])
async def update_routing(payload: RoutingUpdate, db: AsyncSession = Depends(get_db)):
    values = payload.model_dump()
    routing = None
    if values.get("id"):
        routing = (
            await db.execute(select(Routing).where(Routing.id == values["id"]))
        ).scalar_one_or_none()
    if routing is None:
        routing = Routing(id=values.pop("id") or f"ROUTE_{uuid4().hex[:12].upper()}", **{k: v for k, v in values.items() if k != "id"})
        db.add(routing)
    else:
        for field, value in values.items():
            if field != "id":
                setattr(routing, field, value)
    await db.commit()
    await db.refresh(routing)
    return SuccessResponse(data=RoutingResponse.model_validate(routing), message="Cập nhật routing thành công")


@router.delete("/routings/{routing_id}", response_model=SuccessResponse[None], dependencies=[admin_only])
async def delete_routing(routing_id: str, db: AsyncSession = Depends(get_db)):
    routing = (await db.execute(select(Routing).where(Routing.id == routing_id))).scalar_one_or_none()
    if routing is None:
        raise AppException(404, "Không tìm thấy routing")
    await db.delete(routing)
    await db.commit()
    return SuccessResponse(message="Xóa routing thành công")


@router.post("/routings/swap-tables", response_model=SuccessResponse[dict], dependencies=[admin_only])
async def swap_routing_tables(payload: SwapRoutingTablesRequest, db: AsyncSession = Depends(get_db)):
    tables = (
        await db.execute(
            select(Table).where(Table.table_id.in_([payload.table_a_id, payload.table_b_id]))
        )
    ).scalars().all()
    table_qr_ids = {table.table_id: table.qr_id for table in tables}
    if len(table_qr_ids) != 2:
        raise AppException(404, "Không tìm thấy một hoặc cả hai bàn")
    table_a_qr = table_qr_ids[payload.table_a_id]
    table_b_qr = table_qr_ids[payload.table_b_id]
    routes = (
        await db.execute(
            select(Routing).where(
                (Routing.qr_id.in_([table_a_qr, table_b_qr]))
                | (Routing.target_table_id.in_([table_a_qr, table_b_qr]))
            )
        )
    ).scalars().all()
    for route in routes:
        if route.qr_id == table_a_qr:
            route.qr_id = table_b_qr
        elif route.qr_id == table_b_qr:
            route.qr_id = table_a_qr
        if route.target_table_id == table_a_qr:
            route.target_table_id = table_b_qr
        elif route.target_table_id == table_b_qr:
            route.target_table_id = table_a_qr
    await db.commit()
    return SuccessResponse(data={"updated": len(routes)}, message="Hoán đổi ma trận định tuyến thành công")


@router.post("/swap-table", response_model=SuccessResponse[OrderResponse], dependencies=[admin_only])
async def swap_table(payload: SwapTableRequest, db: AsyncSession = Depends(get_db)):
    order = await TableService(db).swap_table(
        order_id=payload.order_id, new_table_id=payload.new_table_id
    )
    return SuccessResponse(data=OrderResponse.model_validate(order), message="Hoán đổi bàn thành công")
