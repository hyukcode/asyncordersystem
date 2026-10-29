from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    OptimisticLockError,
    OrderNotFoundError,
)

from app.models.processed_event import ProcessedEvent

from app.repositories.order_repository import OrderRepository

from app.repositories.processed_event_repository import ProcessedEventRepository

from app.schemas.event import OrderCreatedEvent

from redis.asyncio import Redis

from app.cache.order_cache import OrderCache

ORDER_CONSUMER = "order-worker"

class OrderEventService:
    def __init__(
        self,
        session: AsyncSession,
        redis: Redis,
    ):
        self.session = session
        self.order_repository = OrderRepository(session)

        self.processed_repository = ProcessedEventRepository(session)

        self.cache = OrderCache(redis)

    
    async def handle_order_created(
        self,
        event: OrderCreatedEvent,
    ) -> bool:
        try:
            async with self.session.begin():

                processed = await self.processed_repository.get(
                    consumer_name=ORDER_CONSUMER,
                    event_id=event.event_id,
                )

                if processed is not None:
                    return False
                
                marker = ProcessedEvent(
                    consumer_name=ORDER_CONSUMER,
                    event_id=event.event_id,
                    event_type=event.event_type,
                )

                await self.processed_repository.create(marker)

                order = await self.order_repository.get_by_id(event.payload.order_id)
                
                if order is None:
                    raise OrderNotFoundError(
                        f"order {event.payload.order_id} not found"
                    )

                success = await self.order_repository.update_status_optimistic(
                    order=order,
                    status="PROCESSING",
                )

                if not success:
                    raise OptimisticLockError(
                        f"order {order.id}"
                        "was modified concurrently"
                    )

            # update orders -> commit ->  delete redis cache

            await self.cache.delete(
                event.payload.order_id
            )

            return True

        except IntegrityError:
            processed = await self.processed_repository.get(
                consumer_name=ORDER_CONSUMER,
                event_id=event.event_id,
            )
            if processed is not None:
                return False
            raise


# BEGIN -> INSERT processed_events -> UPDATE orders pending 到 processing -> commit