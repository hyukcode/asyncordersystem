import asyncio
import json

import aio_pika

from app.core.config import settings
from app.core.database import AsyncSessionFactory
from app.mq.rabbitmq import (
    ORDER_QUEUE,
    ORDER_RETRY_QUEUE,
    ORDER_DLQ,
    RETRY_DELAY_MS,
)
from app.schemas.event import OrderCreatedEvent
from app.services.order_event_service import OrderEventService
from app.core.redis_client import create_redis

from  pydantic import ValidationError

MAX_RETRIES = 3

async def republish_message(
    channel: aio_pika.Channel,
    message: aio_pika.IncomingMessage,
    routing_key: str,
    retry_count: str,
) -> None:
    headers = dict(message.headers or {})

    headers["x-retry-count"] = retry_count

    new_message = aio_pika.Message(
        body=message.body,
        content_type=message.content_type,
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        message_id=message.message_id,
        type=message.type,
        headers=headers,
    )
    await channel.default_exchange.publish(
        new_message,
        routing_key=routing_key,
        mandatory=True,
    )

async def handle_message(
    message: aio_pika.IncomingMessage,
    channel: aio_pika.Channel,
    redis,
) -> None:
    headers = message.headers or {}
    retry_count = int(headers.get("x-retry-count", 0))

    try:
        raw = json.loads(message.body.decode("utf-8"))
        event = OrderCreatedEvent.model_validate(raw)

        async with AsyncSessionFactory() as session:
            service = OrderEventService(
                session=session,
                redis=redis,
            )
            processed = await service.handle_order_created(event)
        
        if processed:
            print("processed:", event.event_id)
        else:
            print("duplicate ignored:", event.event_id)
        
        await message.ack()

    except (
        json.JSONDecodeError,
        ValidationError,
    ) as exc:
        print("invalid message -> DLQ:", str(exc))

        await republish_message(
            channel=channel,
            message=message,
            routing_key=ORDER_DLQ,
            retry_count=retry_count,
        )
        await message.ack()
    
    except Exception as exc:
        print("consume failed:", str(exc), "retry:", retry_count)

        if retry_count >= MAX_RETRIES:

            republish_message(
                channel=channel,
                message=message,
                routing_key=ORDER_DLQ,
                retry_count=retry_count,
            )

            await message.ack()

            print(
                "moved to DLQ:",
                message.message_id,
            )

            return

        try:
            await republish_message(
                channel=channel,
                message=message,
                routing_key=ORDER_RETRY_QUEUE,
                retry_count=retry_count+1,
            )
            await message.ack()

            print(
                "scheduled retry:",
                message.message_id,
                retry_count + 1,
            )
        except Exception:

            await message.nack(requeue=True)


async def main() -> None:

    connection = await aio_pika.connect_robust(settings.rabbitmq_url)

    redis = create_redis()

    channel = await connection.channel()

    await channel.set_qos(prefetch_count=10)

    queue = await channel.declare_queue(
        ORDER_QUEUE,
        durable=True,
    )

    # retry queue 等5s 消息过期重新进入 order.created 轻量的延迟重试机制
    await channel.declare_queue(
        ORDER_RETRY_QUEUE,
        durable=True,
        arguments={
            "x-message-ttl": RETRY_DELAY_MS,
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": ORDER_QUEUE,
        },
    )

    # DLQ
    await channel.declare_queue(
        ORDER_DLQ,
        durable=True,
    )

    async def on_message(
        message: aio_pika.IncomingMessage,
    ) -> None:
        await handle_message(
            message=message,
            channel=channel,
            redis=redis,
        )

    await queue.consume(on_message)

    print("order consumer started")

    try:
        await asyncio.Future()
    finally:
        # 启动Consumer -> 建立一次Redis Client -> 处理很多消息 -> Consumer关闭 -> 关闭Redis
        await redis.aclose()
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

# Outbox
#   ↓
# order.created
#   ↓
# Consumer
#   ↓
# 业务成功
#   ↓
# ACK
#   ↓
# 消息删除

# order.created
#       ↓
#    Consumer
#       ↓
#     失败
#       ↓
# order.created.retry
#       ↓
#     5秒
#       ↓
# order.created
#       ↓
# 再次消费

# retry 1
#  ↓
# retry 2
#  ↓
# retry 3
#  ↓
# DLQ

# 非法 JSON
# 或
# Schema 错误

#      ↓

# 直接 DLQ