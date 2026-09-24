"""
app/main.py
------------
Điểm khởi động ứng dụng FastAPI:
- Khởi tạo app, cấu hình CORS.
- Đăng ký Global Exception Handlers (format lỗi đồng nhất).
- Đăng ký router v1.
- Quản lý vòng đời (lifespan): kiểm tra kết nối DB lúc khởi động, dọn dẹp lúc tắt.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import engine
from app.core.exceptions import register_exception_handlers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("robot_backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event thay thế cho @app.on_event("startup")/("shutdown") đã deprecated.
    - Startup: kiểm tra kết nối MySQL để fail-fast nếu cấu hình sai ngay từ đầu.
    - Shutdown: đóng gọn connection pool.
    """
    logger.info("🚀 Đang khởi động %s (env=%s)...", settings.PROJECT_NAME, settings.ENVIRONMENT)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("✅ Kết nối MySQL thành công.")
    except Exception as exc:
        logger.error("❌ Không thể kết nối MySQL lúc khởi động: %s", exc)
        # Không raise ở đây để tránh crash hoàn toàn trong môi trường dev khi DB chưa sẵn sàng,
        # nhưng trong production nên raise để container orchestrator (Docker/K8s) tự restart.

    yield

    logger.info("🛑 Đang tắt ứng dụng, đóng connection pool MySQL...")
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="1.0.0",
        description="Backend API cho hệ thống Robot Phục Vụ Nhà Hàng Tự Động Điều Hướng Bằng Mã QR",
        lifespan=lifespan,
    )

    # ---- CORS: cho phép Frontend (Admin Dashboard / App khách hàng) gọi API ----
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---- Global Exception Handlers: đồng nhất format lỗi trả về ----
    register_exception_handlers(app)

    # ---- Đăng ký router API v1 ----
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.get("/", tags=["Health Check"])
    async def root():
        return {"status": "success", "message": f"{settings.PROJECT_NAME} đang hoạt động"}

    @app.get("/health", tags=["Health Check"])
    async def health_check():
        return {"status": "ok"}

    return app


app = create_app()
