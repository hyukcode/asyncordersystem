from datetime import datetime

from sqlalchemy import (
    DateTime,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

class ProcessedEvent(Base):
    __tablename__ = "processed_events"

    __table_args__ = (
        UniqueConstraint(
            "consumer_name",
            "event_id",
            name="uq_processed_event_consumer_event",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    consumer_name: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    event_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    event_type: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    processed_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

#  UNIQUE(consumer_name, event_id)
# 一个 order.created 同时需要 payment-consumer notification-consumer points-consumer