"""
app/api/v1/endpoints/dishes.py
---------------------------------
CRUD menu món ăn. STAFF chỉ được xem, ADMIN được tạo/sửa.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from uuid import uuid4

from app.core.database import get_db
from app.core.exceptions import AppException
from app.core.security import require_roles
from app.models.category import Category
from app.models.dish import Dish
from app.schemas.common import SuccessResponse
from app.schemas.dish import DishCreate, DishResponse, DishStatusUpdate, DishUpdate

router = APIRouter(prefix="/dishes", tags=["Dishes - Thực đơn"])
admin_router = APIRouter(prefix="/admin/dishes", tags=["Admin - Thực đơn"])


@admin_router.get(
    "",
    response_model=SuccessResponse[list[DishResponse]],
    dependencies=[Depends(require_roles("ADMIN"))],
)
async def admin_list_dishes(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Dish).options(selectinload(Dish.category)).order_by(Dish.dish_name)
    )
    dishes = result.scalars().all()
    return SuccessResponse(data=[DishResponse.model_validate(dish) for dish in dishes])


@router.get("", response_model=SuccessResponse[list[DishResponse]])
async def list_dishes(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Dish)
        .options(selectinload(Dish.category))
        .where(Dish.is_available == True)  # noqa: E712
        .order_by(Dish.dish_name)
    )
    dishes = result.scalars().all()
    return SuccessResponse(data=[DishResponse.model_validate(d) for d in dishes])


@router.get("/{dish_id}", response_model=SuccessResponse[DishResponse])
async def get_dish(dish_id: str, db: AsyncSession = Depends(get_db)):
    dish = (
        await db.execute(
            select(Dish)
            .options(selectinload(Dish.category))
            .where(Dish.dish_id == dish_id)
        )
    ).scalar_one_or_none()
    if dish is None:
        raise AppException(404, "Không tìm thấy món ăn")
    return SuccessResponse(data=DishResponse.model_validate(dish))


@router.post(
    "",
    response_model=SuccessResponse[DishResponse],
    dependencies=[Depends(require_roles("ADMIN"))],
)
async def create_dish(payload: DishCreate, db: AsyncSession = Depends(get_db)):
    values = payload.model_dump()
    category = (
        await db.execute(select(Category).where(Category.category_id == values["category_id"]))
    ).scalar_one_or_none()
    if category is None:
        raise AppException(404, "Không tìm thấy danh mục món ăn")
    dish = Dish(
        dish_id=values.pop("dish_id") or f"DISH_{uuid4().hex[:12].upper()}",
        **values,
    )
    db.add(dish)
    await db.commit()
    await db.refresh(dish)
    return SuccessResponse(data=DishResponse.model_validate(dish), message="Thêm món ăn thành công")


@router.put(
    "/{dish_id}",
    response_model=SuccessResponse[DishResponse],
    dependencies=[Depends(require_roles("ADMIN"))],
)
async def update_dish(dish_id: str, payload: DishUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dish).where(Dish.dish_id == dish_id))
    dish = result.scalar_one_or_none()
    if dish is None:
        raise AppException(status_code=404, message="Không tìm thấy món ăn")

    values = payload.model_dump(exclude_unset=True)
    if "category_id" in values:
        category = (
            await db.execute(select(Category).where(Category.category_id == values["category_id"]))
        ).scalar_one_or_none()
        if category is None:
            raise AppException(404, "Không tìm thấy danh mục món ăn")
    for field, value in values.items():
        setattr(dish, field, value)

    await db.commit()
    dish = (
        await db.execute(
            select(Dish)
            .options(selectinload(Dish.category))
            .where(Dish.dish_id == dish_id)
        )
    ).scalar_one()
    return SuccessResponse(data=DishResponse.model_validate(dish), message="Cập nhật món ăn thành công")


@router.patch(
    "/{dish_id}/status",
    response_model=SuccessResponse[DishResponse],
    dependencies=[Depends(require_roles("ADMIN"))],
)
async def update_dish_status(dish_id: str, payload: DishStatusUpdate, db: AsyncSession = Depends(get_db)):
    dish = (await db.execute(select(Dish).where(Dish.dish_id == dish_id))).scalar_one_or_none()
    if dish is None:
        raise AppException(404, "Không tìm thấy món ăn")
    dish.is_available = payload.is_available
    await db.commit()
    await db.refresh(dish)
    return SuccessResponse(data=DishResponse.model_validate(dish), message="Cập nhật trạng thái món thành công")


@admin_router.post("", response_model=SuccessResponse[DishResponse], dependencies=[Depends(require_roles("ADMIN"))])
async def admin_create_dish(payload: DishCreate, db: AsyncSession = Depends(get_db)):
    return await create_dish(payload, db)


@admin_router.put("/{dish_id}", response_model=SuccessResponse[DishResponse], dependencies=[Depends(require_roles("ADMIN"))])
async def admin_update_dish(dish_id: str, payload: DishUpdate, db: AsyncSession = Depends(get_db)):
    return await update_dish(dish_id, payload, db)


@admin_router.patch("/{dish_id}/status", response_model=SuccessResponse[DishResponse], dependencies=[Depends(require_roles("ADMIN"))])
async def admin_update_dish_status(dish_id: str, payload: DishStatusUpdate, db: AsyncSession = Depends(get_db)):
    return await update_dish_status(dish_id, payload, db)
