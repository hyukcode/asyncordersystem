from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.models.order import Order
from app.schemas.order import OrderResponse

ORDER_CACHE_TTL = 60

class OrderCache:
    def __init__(
        self,
        redis: Redis,
    ):
        self.redis = redis

    @staticmethod
    def key(order_id: int) -> str:
        return f"order:{order_id}"

    async def get(
        self,
        order_id: int,
    ) -> OrderResponse | None:
        try:
            value = await self.redis.get(
                self.key(order_id)
            )
        except RedisError:
            return None
        
        if value is None:
            return None

        return OrderResponse.model_validate_json(value)

    async def set(
        self,
        order: Order,
    ) -> None:
        try:
            data = OrderResponse.model_validate(order)
            await self.redis.set(
                self.key(order.id),
                data.model_dump_json(),
                ex=ORDER_CACHE_TTL,
            )
        except RedisError:
            pass 
    
    async def delete(
        self,
        order_id: int,
    ) -> None:
        try:
            await self.redis.delete(self.key(order_id))
        except RedisError:
            pass
        # redis 正常 加速 redis 挂了 MySQL继续工作
