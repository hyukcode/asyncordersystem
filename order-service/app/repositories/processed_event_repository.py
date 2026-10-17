from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.processed_event import ProcessedEvent

class ProcessedEventRepository:
    def __init__(
        self,
        session: AsyncSession,
    ):
        self.session = session
    
    async def get(
        self,
        consumer_name: str,
        event_id: str,
    ) -> ProcessedEvent | None:
        stmt = (
                select(ProcessedEvent)
                    .where(
                        ProcessedEvent.consumer_name == consumer_name,
                        ProcessedEvent.event_id == event_id,
                    )
            )

        result = await self.session.execute(stmt)

        return result.scalar_one_or_none()

    async def create(
        self,
        event: ProcessedEvent,
    ) -> ProcessedEvent:
        self.session.add(event)

        await self.session.flush()

        return event