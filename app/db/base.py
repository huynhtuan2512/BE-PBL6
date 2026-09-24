"""
app/db/base.py
---------------
Base class dùng chung cho toàn bộ ORM Model (SQLAlchemy 2.0 Declarative Style).
Alembic (migration) sẽ import Base.metadata từ đây để autogenerate migration.
"""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base chung, mọi Model đều kế thừa từ đây."""
    pass


class TimestampMixin:
    """
    Mixin thêm 2 cột created_at / updated_at cho các bảng cần audit thời gian.
    Dùng server_default để MySQL tự set giá trị, tránh lệch giờ giữa app server và DB.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
