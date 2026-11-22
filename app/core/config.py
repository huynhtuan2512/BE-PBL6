"""Application settings."""

from functools import lru_cache
from typing import List

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Robot Phuc Vu Nha Hang API"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DATABASE_URL: str = "mysql+aiomysql://root:root@localhost:3306/restaurant_data"

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    DEVICE_API_KEY: str = Field(
        validation_alias=AliasChoices("DEVICE_API_KEY", "X_DEVICE_KEY"),
    )

    ROBOT_MAX_IMAGE_BYTES: int = 8 * 1024 * 1024
    ROBOT_COMMAND_FALLBACK_POLL_SECONDS: float = 5.0

    THINGSBOARD_HOST: str = "localhost"
    THINGSBOARD_MQTT_PORT: int = 1883
    THINGSBOARD_REST_URL: str = "http://localhost:8080"
    THINGSBOARD_USERNAME: str | None = None
    THINGSBOARD_PASSWORD: str | None = None

    BACKEND_CORS_ORIGINS: List[str] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, value):
        if isinstance(value, str) and not value.startswith("["):
            return [origin.strip() for origin in value.split(",") if origin]
        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
