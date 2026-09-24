"""
app/core/database.py
---------------------
Khởi tạo Async SQLAlchemy Engine kết nối MySQL và cung cấp
dependency `get_db` để inject AsyncSession vào các endpoint FastAPI.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# ---------------------------------------------------------------------------
# Async Engine: quản lý pool kết nối tới MySQL (driver aiomysql)
# ---------------------------------------------------------------------------
engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=(settings.ENVIRONMENT == "development"),  # log SQL khi dev để debug
    pool_pre_ping=True,   # kiểm tra connection còn sống trước khi dùng (tránh lỗi mất kết nối MySQL)
    pool_recycle=3600,    # recycle connection sau 1h, tránh MySQL tự đóng kết nối "wait_timeout"
    pool_size=10,
    max_overflow=20,
    future=True,
)

# ---------------------------------------------------------------------------
# Session Factory: mỗi request sẽ tạo 1 AsyncSession riêng biệt
# expire_on_commit=False để có thể truy cập object sau khi commit (tránh lazy-load lỗi async)
# ---------------------------------------------------------------------------
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency Injection cho FastAPI: `db: AsyncSession = Depends(get_db)`.
    Đảm bảo session luôn được đóng lại sau khi request kết thúc,
    và rollback tự động nếu có exception xảy ra giữa chừng.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
