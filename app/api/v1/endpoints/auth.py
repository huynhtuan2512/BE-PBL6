"""
app/api/v1/endpoints/auth.py
------------------------------
Đăng nhập cho ADMIN / STAFF, trả về JWT access token.
"""

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AppException
from app.core.security import create_access_token, get_current_user, verify_password
from app.models.user import User
from app.schemas.auth import UserResponse
from app.schemas.common import SuccessResponse, Token

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=Token, summary="Đăng nhập bằng username/password, nhận JWT token")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Dùng OAuth2PasswordRequestForm để tương thích chuẩn OAuth2 Bearer Token
    (Swagger UI sẽ tự hiển thị form username/password khi bấm nút Authorize).
    """
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(form_data.password, user.password_hash):
        raise AppException(status_code=401, message="Sai tên đăng nhập hoặc mật khẩu")

    if not user.is_active:
        raise AppException(status_code=403, message="Tài khoản đã bị vô hiệu hóa")

    # Cần load role để lấy tên role đưa vào token claim
    await db.refresh(user, attribute_names=["role"])

    access_token = create_access_token(subject=user.id, role=user.role.name)
    return Token(access_token=access_token, role=user.role.name)


@router.get("/me", response_model=SuccessResponse[UserResponse], summary="Lấy thông tin tài khoản đang đăng nhập")
async def get_me(current_user: User = Depends(get_current_user)):
    return SuccessResponse(data=UserResponse.model_validate(current_user))
