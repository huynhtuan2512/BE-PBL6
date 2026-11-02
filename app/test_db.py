"""Kiểm tra nhanh kết nối database của backend.

Chạy từ thư mục BE bằng:
    python -m app.test_db
"""

import asyncio
import os
import sys

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


load_dotenv()


async def test_database_connection() -> int:
    """Thử kết nối database và trả về mã thoát của chương trình."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("KET NOI THAT BAI: Chua co DATABASE_URL trong file .env")
        return 1

    engine = create_async_engine(database_url, pool_pre_ping=True)

    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
            print("KET NOI THANH CONG")
            return 0
    except Exception as exc:
        print(f"KET NOI THAT BAI: {exc}")
        return 1
    finally:
        await engine.dispose()


if __name__ == "__main__":
    sys.exit(asyncio.run(test_database_connection()))
