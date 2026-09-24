"""
app/core/config.py
-------------------
Quản lý cấu hình toàn cục của ứng dụng bằng Pydantic Settings (v2).
Tự động đọc biến môi trường từ file .env, có validate kiểu dữ liệu.
"""

from functools import lru_cache
from typing import List

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ---- Thông tin chung của dự án ----
    PROJECT_NAME: str = "Robot Phuc Vu Nha Hang API"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"  # development | production

    # ---- Database (MySQL - Async) ----
    # Ví dụ: mysql+aiomysql://user:password@host:3306/db_name
    DATABASE_URL: str

    # ---- JWT Authentication (dành cho ADMIN / STAFF) ----
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 tiếng / ca làm việc

    # ---- Static API Key (dành cho ESP32_ROBOT / RASPBERRY_PI) ----
    # Thiết bị IoT không đăng nhập bằng JWT mà dùng Header "X-Device-Key"
    DEVICE_API_KEY: str

    # ---- ThingsBoard IoT Platform ----
    THINGSBOARD_HOST: str = "localhost"
    THINGSBOARD_MQTT_PORT: int = 1883
    THINGSBOARD_REST_URL: str = "http://localhost:8080"
    THINGSBOARD_USERNAME: str | None = None
    THINGSBOARD_PASSWORD: str | None = None

    # ---- CORS ----
    BACKEND_CORS_ORIGINS: List[str] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        # Cho phép truyền dạng chuỗi "a,b,c" hoặc list JSON trong .env
        if isinstance(v, str) and not v.startswith("["):
            return [origin.strip() for origin in v.split(",") if origin]
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """
    Cache lại Settings để không phải đọc/parse file .env nhiều lần
    trong suốt vòng đời ứng dụng (dùng như Singleton).
    """
    return Settings()


settings = get_settings()
