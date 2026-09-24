"""
app/api/v1/endpoints/dishes.py
---------------------------------
CRUD menu món ăn. STAFF chỉ được xem, ADMIN được tạo/sửa.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AppException
from app.core.security import require_roles
from app.models.dish import Dish
from app.schemas.common import SuccessResponse
from app.schemas.dish import DishCreate, DishResponse, DishUpdate

router = APIRouter(prefix="/dishes", tags=["Dishes - Thực đơn"])


@router.get("", response_model=SuccessResponse[list[DishResponse]])
async def list_dishes(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dish).where(Dish.is_available == True))  # noqa: E712
    dishes = result.scalars().all()
    return SuccessResponse(data=[DishResponse.model_validate(d) for d in dishes])


@router.post(
    "",
    response_model=SuccessResponse[DishResponse],
    dependencies=[Depends(require_roles("ADMIN"))],
)
async def create_dish(payload: DishCreate, db: AsyncSession = Depends(get_db)):
    dish = Dish(**payload.model_dump())
    db.add(dish)
    await db.commit()
    await db.refresh(dish)
    return SuccessResponse(data=DishResponse.model_validate(dish), message="Thêm món ăn thành công")


@router.put(
    "/{dish_id}",
    response_model=SuccessResponse[DishResponse],
    dependencies=[Depends(require_roles("ADMIN"))],
)
async def update_dish(dish_id: int, payload: DishUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dish).where(Dish.id == dish_id))
    dish = result.scalar_one_or_none()
    if dish is None:
        raise AppException(status_code=404, message="Không tìm thấy món ăn")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(dish, field, value)

    await db.commit()
    await db.refresh(dish)
    return SuccessResponse(data=DishResponse.model_validate(dish), message="Cập nhật món ăn thành công")
