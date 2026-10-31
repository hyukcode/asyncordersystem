import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from worker import outbox_consumer as consumer

class FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

def build_message():
    message = MagicMock()

    message.body = json.dumps({
        "event_id": "test-event-001",
        "event_type": "order.created",
        "payload": {
            "order_id": 1,
            "order_no": "order-001",
            "user_id": 1001,
            "amount": "100.00",
            "status": "PENDING",
        },
    }).encode("utf-8")

    message.headers = {
        "x-retry-count": 3,
    }

    message.message_id = "test-event-001"
    message.ack = AsyncMock()
    message.nack = AsyncMock()

    return message

def mock_business_failure(monkeypatch):
    # 不访问真实 MySQL
    monkeypatch.setattr(
        consumer,
        "AsyncSessionFactory",
        lambda: FakeSession(),
    )

    failed_handler = AsyncMock(
        side_effect=RuntimeError("simulated DB failure")
    )

    monkeypatch.setattr(
        consumer,
        "OrderEventService",
        lambda session, redis: SimpleNamespace(
            handle_order_created=failed_handler
        ),
    )


@pytest.mark.asyncio
async def test_max_retries_sends_to_dlq(monkeypatch):
    mock_business_failure(monkeypatch)

    message = build_message()

    publish = AsyncMock()

    monkeypatch.setattr(
        consumer,
        "republish_message",
        publish,
    )

    await consumer.handle_message(
        message=message,
        channel=MagicMock(),
        redis=MagicMock(),
    )

    # 必须真正 await 发布到 DLQ
    publish.assert_awaited_once()

    assert (
        publish.await_args.kwargs["routing_key"]
        == consumer.ORDER_DLQ
    )

    # DLQ 发布成功后确认原消息
    message.ack.assert_awaited_once()
    message.nack.assert_not_awaited()


@pytest.mark.asyncio
async def test_dlq_publish_failure_nacks(monkeypatch):
    mock_business_failure(monkeypatch)

    message = build_message()

    # 模拟 RabbitMQ 发布 DLQ 失败
    publish = AsyncMock(
        side_effect=RuntimeError("RabbitMQ unavailable")
    )

    monkeypatch.setattr(
        consumer,
        "republish_message",
        publish,
    )

    await consumer.handle_message(
        message=message,
        channel=MagicMock(),
        redis=MagicMock(),
    )

    # DLQ 发布失败时不能 ACK
    message.ack.assert_not_awaited()

    # 原消息需要重新入队
    message.nack.assert_awaited_once_with(
        requeue=True
    )