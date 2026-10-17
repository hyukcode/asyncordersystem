from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outbox_event import OutboxEvent

class OutboxRepository:
    def __init__(
        self,
        session: AsyncSession,
    ):
        self.session = session
    
    async def create(
        self,
        event: OutboxEvent,
    ) -> OutboxEvent:
        self.session.add(event)

        await self.session.flush()

        return event

    async def get_pending_batch(
        self,
        limit: int = 20,
    ) -> list[OutboxEvent]:
    # workerA workerB 多个 worker 可以并行消费 Outbox
        stmt = (
            select(OutboxEvent)
            .where(
                OutboxEvent.status == "PENDING"
            )
            .order_by(
                OutboxEvent.created_at,
                OutboxEvent.id,
            )
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        result = await self.session.execute(stmt)

        return list(result.scalars().all())

    async def mark_published(
        self,
        event_id: int,
    ) -> None:
        stmt = (
            update(OutboxEvent)
            .where(OutboxEvent.id == event_id)
            .values(
                status="PUBLISHED",
                published_at=func.now(),
                last_error=None,
            )
        )
        await self.session.execute(stmt)

    async def mark_failed(
        self,
        event: OutboxEvent,
        error: str,
        max_retries: int = 5,
    ) -> None:
        retry_count = event.retry_count + 1

        status = (
            "FAILED"
            if retry_count >= max_retries
            else "PENDING"
        )

        stmt = (
            update(OutboxEvent)
            .where(OutboxEvent.id == event.id)
            .values(
                status=status,
                retry_count=retry_count,
                last_error=error[:500],
            )
        )

        await self.session.execute(stmt)