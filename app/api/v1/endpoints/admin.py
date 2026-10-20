"""Administration endpoints backed by tables present in restaurant.sql."""

from uuid import uuid4

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.exceptions import AppException
from app.core.security import hash_password, require_roles
from app.models.order import Order
from app.models.user import Role, User
from app.schemas.admin import RoleResponse, SwapTableRequest, UserCreate, UserResponse, UserUpdate
from app.schemas.common import SuccessResponse
from app.schemas.order import OrderResponse
from app.services.table_service import TableService

router = APIRouter(prefix="/admin", tags=["Admin - Quản trị hệ thống"])
admin_only = Depends(require_roles("ADMIN"))


@router.get("/roles", response_model=SuccessResponse[list[RoleResponse]], dependencies=[admin_only])
async def list_roles(db: AsyncSession = Depends(get_db)):
    roles = (await db.execute(select(Role).order_by(Role.role_name))).scalars().all()
    return SuccessResponse(data=[RoleResponse.model_validate(role) for role in roles])


@router.post("/users", response_model=SuccessResponse[dict], dependencies=[admin_only])
async def create_user(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    values = payload.model_dump()
    user = User(
        user_id=values.pop("user_id") or f"USER_{uuid4().hex[:12].upper()}",
        password_hash=hash_password(values.pop("password")),
        **values,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise AppException(409, "Tên đăng nhập hoặc mã vai trò không hợp lệ") from exc
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
    query = select(User).options(selectinload(User.role)).order_by(User.user_id.desc())
    count_query = select(func.count(User.user_id))
    if search:
        search_filter = User.username.ilike(f"%{search}%") | User.full_name.ilike(f"%{search}%")
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    users = (
        await db.execute(query.offset((page - 1) * page_size).limit(page_size))
    ).scalars().all()
    total = (await db.execute(count_query)).scalar_one()
    return SuccessResponse(
        data={
            "items": [UserResponse.model_validate(user) for user in users],
            "page": page,
            "page_size": page_size,
            "total": total,
        }
    )


@router.put(
    "/users/{user_id}",
    response_model=SuccessResponse[UserResponse],
    dependencies=[admin_only],
)
async def update_user(user_id: str, payload: UserUpdate, db: AsyncSession = Depends(get_db)):
    user = (
        await db.execute(
            select(User).options(selectinload(User.role)).where(User.user_id == user_id)
        )
    ).scalar_one_or_none()
    if user is None:
        raise AppException(404, "Không tìm thấy tài khoản")

    values = payload.model_dump(exclude_unset=True)
    new_password = values.pop("new_password", None)
    if new_password is not None:
        target_role_id = values.get("role_id", user.role_id)
        target_role = (
            await db.execute(select(Role).where(Role.role_id == target_role_id))
        ).scalar_one_or_none()
        if target_role is None:
            raise AppException(404, "Không tìm thấy vai trò")
        if target_role.role_name != "STAFF":
            raise AppException(409, "Chỉ có thể đặt lại mật khẩu cho tài khoản nhân viên")
        user.password_hash = hash_password(new_password)

    for field, value in values.items():
        setattr(user, field, value)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise AppException(404, "Không tìm thấy vai trò") from exc
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


@router.post(
    "/swap-table",
    response_model=SuccessResponse[OrderResponse],
    dependencies=[admin_only],
    summary="Chuyển đơn hàng sang bàn đang trống và cập nhật trạng thái hai bàn",
)
async def swap_table(payload: SwapTableRequest, db: AsyncSession = Depends(get_db)):
    order = await TableService(db).swap_table(
        order_id=payload.order_id,
        new_table_id=payload.new_table_id,
    )
    return SuccessResponse(data=OrderResponse.model_validate(order), message="Chuyển bàn thành công")
