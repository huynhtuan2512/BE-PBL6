"""Menu category endpoints."""

from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AppException
from app.core.security import require_roles
from app.models.category import Category
from app.models.dish import Dish
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate
from app.schemas.common import SuccessResponse

router = APIRouter(prefix="/categories", tags=["Categories - Danh mục"])
admin_only = Depends(require_roles("ADMIN"))


@router.get("", response_model=SuccessResponse[list[CategoryResponse]])
async def list_categories(db: AsyncSession = Depends(get_db)):
    categories = (
        await db.execute(select(Category).order_by(Category.category_name))
    ).scalars().all()
    return SuccessResponse(data=[CategoryResponse.model_validate(category) for category in categories])


@router.post(
    "",
    response_model=SuccessResponse[CategoryResponse],
    dependencies=[admin_only],
)
async def create_category(payload: CategoryCreate, db: AsyncSession = Depends(get_db)):
    category = Category(
        category_id=payload.category_id or f"CAT_{uuid4().hex[:12].upper()}",
        category_name=payload.category_name.strip(),
        description=payload.description,
    )
    db.add(category)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise AppException(409, "Tên hoặc mã danh mục đã tồn tại") from exc
    await db.refresh(category)
    return SuccessResponse(data=CategoryResponse.model_validate(category), message="Tạo danh mục thành công")


@router.put(
    "/{category_id}",
    response_model=SuccessResponse[CategoryResponse],
    dependencies=[admin_only],
)
async def update_category(
    category_id: str,
    payload: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
):
    category = (
        await db.execute(select(Category).where(Category.category_id == category_id))
    ).scalar_one_or_none()
    if category is None:
        raise AppException(404, "Không tìm thấy danh mục")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(category, field, value.strip() if field == "category_name" and value else value)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise AppException(409, "Tên danh mục đã tồn tại") from exc
    await db.refresh(category)
    return SuccessResponse(data=CategoryResponse.model_validate(category), message="Cập nhật danh mục thành công")


@router.delete("/{category_id}", response_model=SuccessResponse[None], dependencies=[admin_only])
async def delete_category(category_id: str, db: AsyncSession = Depends(get_db)):
    category = (
        await db.execute(select(Category).where(Category.category_id == category_id))
    ).scalar_one_or_none()
    if category is None:
        raise AppException(404, "Không tìm thấy danh mục")
    has_dishes = await db.execute(
        select(Dish.dish_id).where(Dish.category_id == category_id).limit(1)
    )
    if has_dishes.scalar_one_or_none() is not None:
        raise AppException(409, "Không thể xóa danh mục đang có món ăn")
    await db.delete(category)
    await db.commit()
    return SuccessResponse(message="Xóa danh mục thành công")
