"""
app/core/security.py
---------------------
Xử lý 2 luồng xác thực song song của hệ thống:

1) OAuth2 Bearer + JWT      -> dành cho con người: ADMIN / STAFF (đăng nhập bằng username/password).
2) Static Header X-Device-Key -> dành cho thiết bị IoT: ESP32_ROBOT / RASPBERRY_PI
   (thiết bị không có UI đăng nhập nên dùng khóa tĩnh cấu hình sẵn, đơn giản & nhanh cho MCU).
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import AppException

# ============================================================================
# 1. PASSWORD HASHING (dùng bcrypt cho tài khoản ADMIN / STAFF)
# ============================================================================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# ============================================================================
# 2. JWT TOKEN
# ============================================================================
# tokenUrl trỏ tới endpoint login thực tế để Swagger UI hiển thị nút "Authorize"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")


def create_access_token(subject: str, role: str, extra_claims: dict[str, Any] | None = None) -> str:
    """
    Tạo JWT access token chứa: sub (user id), role (ADMIN/STAFF), exp (hạn dùng).
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {"sub": str(subject), "role": role, "exp": expire}
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as exc:
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message="Token không hợp lệ hoặc đã hết hạn",
        ) from exc


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    """
    Dependency dùng cho các endpoint yêu cầu đăng nhập (ADMIN/STAFF).
    Giải mã JWT -> lấy user_id -> truy vấn DB để đảm bảo user còn tồn tại & active.
    """
    # import cục bộ để tránh circular import giữa security.py và models
    from app.models.user import User

    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if user_id is None:
        raise AppException(status_code=status.HTTP_401_UNAUTHORIZED, message="Token thiếu thông tin người dùng")

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise AppException(status_code=status.HTTP_401_UNAUTHORIZED, message="Tài khoản không tồn tại hoặc đã bị khóa")

    return user


def require_roles(*allowed_roles: str):
    """
    Factory tạo dependency kiểm tra phân quyền theo vai trò.
    Cách dùng: Depends(require_roles("ADMIN"))
    """

    async def role_checker(current_user=Depends(get_current_user)):
        if current_user.role.name not in allowed_roles:
            raise AppException(
                status_code=status.HTTP_403_FORBIDDEN,
                message=f"Yêu cầu quyền: {', '.join(allowed_roles)}",
            )
        return current_user

    return role_checker


# ============================================================================
# 3. DEVICE API KEY (ESP32_ROBOT / RASPBERRY_PI)
# ============================================================================
async def verify_device_key(x_device_key: str | None = Header(default=None, alias="X-Device-Key")) -> str:
    """
    Xác thực thiết bị phần cứng bằng static API Key gửi qua Header `X-Device-Key`.
    Không dùng JWT vì ESP32/Raspberry Pi cần cơ chế xác thực đơn giản, ít overhead,
    không cần luồng refresh-token phức tạp.
    """
    if x_device_key is None or x_device_key != settings.DEVICE_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Device-Key không hợp lệ hoặc bị thiếu",
        )
    return x_device_key
