import asyncio

from app.core.database import AsyncSessionFactory
from app.mq.rabbitmq import rabbitmq_publisher
from app.repositories.outbox_repository import OutboxRepository

POLL_INTERVAL_SECONDS = 1
BATCH_SIZE = 20

async def publish_batch() -> int:
    async with AsyncSessionFactory() as session:
        async with session.begin():
            repository = OutboxRepository(session)
            events = await repository.get_pending_batch(limit=BATCH_SIZE)
            for event in events:
                try:
                    await rabbitmq_publisher.publish_event(
                        event_id=event.event_id,
                        event_type=event.event_type,
                        payload=event.payload,
                    )

                    await repository.mark_published(event.id)

                    print("published:", event.event_id, event.event_type)
                
                except Exception as exc:
                    await repository.mark_failed(event, str(exc))
                    print("publish failed:", event.event_id, str(exc))
            return len(events)

async def main() -> None:
    await rabbitmq_publisher.connect()
    print("outbox publisher started")
    try:
        while True:
            count = await publish_batch()
            if count == 0:
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
    finally:
        await rabbitmq_publisher.close()

if __name__ == "__main__":
    asyncio.run(main())

# Terminal A  uvicorn app.main:app --reload

# http -> orders + outbox_events

# Terminal B

# outbox_events -> RabbitMQ

# 后面部署会有 order-api container / outbox-publisher container