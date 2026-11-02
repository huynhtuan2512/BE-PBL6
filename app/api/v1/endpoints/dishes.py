"""
app/api/v1/endpoints/dishes.py
---------------------------------
CRUD menu món ăn. STAFF chỉ được xem, ADMIN được tạo/sửa.
"""

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from app.core.database import get_db
from app.core.exceptions import AppException
from app.core.security import require_roles
from app.core.storage import DISH_IMAGES_DIR
from app.models.dish import Dish
from app.schemas.common import SuccessResponse
from app.schemas.dish import DishCreate, DishResponse, DishStatusUpdate, DishUpdate

router = APIRouter(prefix="/dishes", tags=["Dishes - Thực đơn"])
admin_router = APIRouter(prefix="/admin/dishes", tags=["Admin - Thực đơn"])

MAX_IMAGE_SIZE = 5 * 1024 * 1024
IMAGE_EXTENSIONS = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


def has_valid_image_signature(content: bytes, content_type: str) -> bool:
    if content_type == "image/jpeg":
        return content.startswith(b"\xff\xd8\xff")
    if content_type == "image/png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")
    return len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP"


@router.get("", response_model=SuccessResponse[list[DishResponse]])
async def list_dishes(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dish).where(Dish.is_available == True))  # noqa: E712
    dishes = result.scalars().all()
    return SuccessResponse(data=[DishResponse.model_validate(d) for d in dishes])


@router.get("/{dish_id}", response_model=SuccessResponse[DishResponse])
async def get_dish(dish_id: str, db: AsyncSession = Depends(get_db)):
    dish = (await db.execute(select(Dish).where(Dish.dish_id == dish_id))).scalar_one_or_none()
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

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(dish, field, value)

    await db.commit()
    await db.refresh(dish)
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


@admin_router.post("/{dish_id}/image", response_model=SuccessResponse[DishResponse], dependencies=[Depends(require_roles("ADMIN"))])
async def upload_dish_image(
    dish_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    extension = IMAGE_EXTENSIONS.get(file.content_type or "")
    if extension is None:
        raise AppException(415, "Chỉ chấp nhận ảnh JPEG, PNG hoặc WebP")

    content = await file.read(MAX_IMAGE_SIZE + 1)
    if len(content) > MAX_IMAGE_SIZE:
        raise AppException(413, "Ảnh không được vượt quá 5 MB")
    if not has_valid_image_signature(content, file.content_type or ""):
        raise AppException(415, "Nội dung file không phải ảnh hợp lệ")

    dish = (await db.execute(select(Dish).where(Dish.dish_id == dish_id))).scalar_one_or_none()
    if dish is None:
        raise AppException(404, "Không tìm thấy món ăn")

    DISH_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{extension}"
    image_path = DISH_IMAGES_DIR / filename
    image_path.write_bytes(content)
    previous_image_url = dish.image_url
    dish.image_url = f"/uploads/dishes/{filename}"

    try:
        await db.commit()
        await db.refresh(dish)
    except Exception:
        await db.rollback()
        image_path.unlink(missing_ok=True)
        raise

    if previous_image_url and previous_image_url.startswith("/uploads/dishes/"):
        previous_path = DISH_IMAGES_DIR / previous_image_url.rsplit("/", 1)[-1]
        if previous_path.resolve().parent == DISH_IMAGES_DIR.resolve() and previous_path != image_path:
            previous_path.unlink(missing_ok=True)

    return SuccessResponse(
        data=DishResponse.model_validate(dish),
        message="Tải ảnh món ăn thành công",
    )


@admin_router.patch("/{dish_id}/status", response_model=SuccessResponse[DishResponse], dependencies=[Depends(require_roles("ADMIN"))])
async def admin_update_dish_status(dish_id: str, payload: DishStatusUpdate, db: AsyncSession = Depends(get_db)):
    return await update_dish_status(dish_id, payload, db)
