import asyncio
import json

import aio_pika

from app.core.config import settings
from app.core.database import AsyncSessionFactory
from app.mq.rabbitmq import ORDER_QUEUE
from app.schemas.event import OrderCreatedEvent
from app.services.order_event_service import OrderEventService

async def handle_message(
    message: aio_pika.IncomingMessage,
) -> None:
    try:
        raw = json.loads(message.body.decode("utf-8"))
        event = OrderCreatedEvent.model_validate(raw)

        async with AsyncSessionFactory() as session:
            service = OrderEventService(session)
            processed = await service.handle_order_created(event)
        
        if processed:
            print("processed:", event.event_id)
        else:
            print("duplicate ignored:", event.event_id)
        
        await message.ack()
    
    except Exception as exc:
        print("consume failed:", str(exc))
        await message.nack(requeue=True)

async def main() -> None:
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)

    channel = await connection.channel()

    await channel.set_qos(prefetch_count=10)

    queue = await channel.declare_queue(
        ORDER_QUEUE,
        durable=True,
    )

    await queue.consume(handle_message)

    print("order consumer started")

    try:
        await asyncio.Future()
    finally:
        await connection.close()

if __name__ == "__main__":
    asyncio.run(main())

# Process 1 FastAPI uvicorn app.main:app

# Process 2 Outbox Relay python -m worker.outbox_publisher

# Process 3 Order Consumer python -m worker.order_consumer

# FastAPI
# |
# MySQL - outbox - Outbox Relay - RabbitMQ - Order Consumer - MySQL - processed_event(event_id)
# ｜                                                             |
# orders                                                      order.status
#                                                           PENDING -> PROCESSING