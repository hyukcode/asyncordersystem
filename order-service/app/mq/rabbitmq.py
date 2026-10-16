import json

import aio_pika

from app.core.config import settings

ORDER_QUEUE = "order.created"

class RabbitMQPublisher:

    def __init__(self):
        self.connection = None
        self.channel = None
    
    # AMQP 一个 TCP Connection + 多个轻量 Channel
    async def connect(self) -> None:
        # connect 连接断了 -> 自己处理
        # connect_robust 长期运行服务，网络抖动，RabbitMQ重连
        self.connection = await aio_pika.connect_robust(
            settings.rabbitmq_url
        )
        # Broker 告诉 Publisher 消息已接管
        self.channel = await self.connection.channel(
            publisher_confirms=True
        )
        # durable 为 true  rabbitmq重启 -> Queue定义仍然存在、
        # durable queue 不等于 消息一定持久化
        await self.channel.declare_queue(
            ORDER_QUEUE,
            durable=True,
        )

    async def publish_order_created(
        self,
        order_id: int,
        order_no: str,
        user_id: int,
    ) -> None:
        if self.channel is None:
            raise RuntimeError(
                "RabbitMQ is not connected"
            )
        
        payload = {
            "event": "order.created",
            "order_id": order_id,
            "order_no": order_no,
            "user_id": user_id,
        }

        # Queue durable + Message persistent 
        message = aio_pika.Message(
            body=json.dumps(payload).encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )

        await self.channel.default_exchange.publish(
            message,
            routing_key=ORDER_QUEUE,
        )

    async def close(self) -> None:
        if self.connection is not None:
            await self.connection.close()

rabbitmq_publisher = RabbitMQPublisher()