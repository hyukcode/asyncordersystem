# INSERT order -> commit -> publish RabbitMQ

# 变成

# BEGIN -> INSERT orders | INSERT outbox_events -> COMMIT 

from datetime import datetime

from typing import Any 

from sqlalchemy import (
    DateTime,
    Index,
    Integer,
    JSON,
    String,
    func,
)

from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    __table_args__ = (
        Index(
            "ix_outbox_status_created_at",
            "status",
            "created_at",
        ),
    )

    # 数据库内部标识
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # 消息的全局唯一ID 后面 Consumer 用它做幂等 （事件世界）
    event_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
    )

    # order
    aggregate_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    # order.id
    aggregate_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    # order.created
    event_type: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    # 真正发送给 RabbitMQ 的消息内容
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )

    # PENDING / PUBLISHED / FAILED
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="PENDING",
        server_default="PENDING",
    )

    # 发布失败次数
    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    last_error: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )