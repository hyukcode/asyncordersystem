import uuid
import hashlib
import json
import logging

from fastapi import HTTPException

from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.core.redis_lock import RedisLock
from redis.exceptions import RedisError
from app.repositories.order_repository import OrderRepository
from app.schemas.order import OrderCreate, OrderStatusUpdate
from app.core.exceptions import (
    InvalidOrderStatusTransitionError,
    OptimisticLockError,
    OrderNotFoundError,
)
# from app.mq.rabbitmq import rabbitmq_publisher

from redis.asyncio import Redis

from app.repositories.outbox_repository import OutboxRepository
from app.models.outbox_event import OutboxEvent
from app.cache.order_cache import OrderCache

logger = logging.getLogger(__name__)

# 状态机规则
STATUS_TRANSITIONS = {
    "PENDING": {
        "PROCESSING",
        "FAILED",
    },
    "PROCESSING": {
        "SUCCESS",
        "FAILED",
    },
    "SUCCESS": set(),
    "FAILED": set(),
}

class OrderService:
    def __init__(
        self, 
        session: AsyncSession,
        redis: Redis,
    ):
        self.session = session
        self.redis = redis
        # OrderRepository OutboxRepository 共享同一个session
        self.repository = OrderRepository(session)
        self.outbox_repository = OutboxRepository(session)
        self.cache = OrderCache(redis)

    @staticmethod
    def request_hash(data: OrderCreate) -> str:

        payload = {
            "user_id": data.user_id,
            "amount": str(data.amount.quantize(Decimal("0.01"))),
        }

        content = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        )

        return hashlib.sha256(
            content.encode("utf-8")
        ).hexdigest()

    async def _find_existing(
        self,
        key: str,
        fingerprint: str,
    ) -> Order | None:

        order = await self.repository.get_by_idempotency_key(key)

        if order is not None:
            if order.request_hash != fingerprint:
                raise HTTPException(
                    status_code=409,
                    detail="Idempotency key reused with different parameters"
                )
        return order

# tuple[Order, bool] 返回订单和是否新建成功的标识，区分首次创建和重复请求
    async def create_order(
        self,
        data: OrderCreate,
        # idempotency_key 请求携带，数据库 unique constraint
        idempotency_key: str,
    ) -> tuple[Order, bool]:
        
        fingerprint = self.request_hash(data)

        lock_name = (
            "order:lock:"
            + hashlib.sha256(
                idempotency_key.encode("utf-8")
            ).hexdigest()
        )

        lock = RedisLock(
            self.redis,
            key=lock_name,
            ttl=30,
        )
        
        try:
            acquired = await lock.acquire()
        except RedisError as exc:
            raise HTTPException(
                status_code=503,
                detail="Redis lock unavailable",
                headers={"Retry-After": "1"}
            ) from exc

        if not acquired:
            existing = await self._find_existing(
                idempotency_key,
                fingerprint,
            )

            if existing is not None:
                return existing, False
            
            raise HTTPException(
                status_code=409,
                detail="Order is being processed. Retry later.",
                headers={"Retry-After": "1"},
            )

        try:
            existing = await self._find_existing(
                idempotency_key,
                fingerprint,
            )

            if existing is not None:
                return existing, False

            order = Order(
                order_no=uuid.uuid4().hex,
                user_id=data.user_id,
                amount=data.amount,
                status="PENDING",
                idempotency_key=idempotency_key,
                request_hash=fingerprint,
            )

            try:
                order = await self.repository.create(order)

                event = OutboxEvent(
                    event_id=uuid.uuid4().hex,
                    aggregate_type="order",
                    aggregate_id=str(order.id),
                    event_type="order.created",
                    payload={
                        "order_id": order.id,
                        "order_no": order.order_no,
                        "user_id": order.user_id,
                        "amount": str(order.amount),
                        "status": order.status,
                    },
                    status="PENDING",
                )

                await self.outbox_repository.create(event)

                await self.session.commit()
            
            except IntegrityError:
                await self.session.rollback()

                existing = await self._find_existing(
                    idempotency_key,
                    fingerprint,
                )

                if existing is not None:
                    return existing, False
                raise

            except Exception:
                await self.session.rollback()
                raise

            await self.session.refresh(order)

        # await rabbitmq_publisher.publish_order_created(
        #     order_id=order.id,
        #     order_no=order.order_no,
        #     user_id=order.user_id,
        # )

            return order, True
        
        finally:
            try:
                await lock.release()
            except RedisError:
                logger.exception(
                    "Redis lock release failed: %s", lock_name
                )
            

    # GET /orders/10
    #    ↓
    # Redis GET order:10
    #     ↓
    # Cache Miss
    #     ↓
    # SELECT MySQL
    #     ↓
    # 找到 Order
    #     ↓
    # SET order:10 EX 60
    #     ↓
    # 返回

    # GET /orders/10
    #    ↓
    # Redis GET order:10
    #     ↓
    #     Cache Hit
    #     ↓
    # 直接返回

    async def get_order(
        self,
        order_id: int,
    ) -> Order | None:
        cached = await self.cache.get(order_id)

        if cached is not None:
            return cached

        order =  await self.repository.get_by_id(
            order_id
        )

        if order is None:
            return None

        await self.cache.set(order)

        return order

    async def update_order_status(
        self,
        order_id: int,
        data: OrderStatusUpdate,
    ) -> Order | None:
        order = await self.repository.get_by_id(order_id)
        if order is None:
            raise OrderNotFoundError(
                f"order {order_id} not found"
            )

        allowed_statuses = STATUS_TRANSITIONS.get(
            order.status,
            set(),
        )

        if data.status not in allowed_statuses:
            raise InvalidOrderStatusTransitionError(
                f"invalid status transition: "
                f"{order.status} -> {data.status}"
            )

        try:
            success = await self.repository.update_status_optimistic(
                order=order,
                status=data.status,
            )
            if not success:

                raise OptimisticLockError(
                    f"order {order_id} was modified"
                    "by another request"
                )

            # 先更新 DB -> commit -> 删缓存
            
            await self.session.commit()

            await self.cache.delete(order_id)

            return await self.repository.get_by_id(order_id)
        except Exception:
            await self.session.rollback()
            raise

        # domain exception -> service -> fastapi execption handler -> 409 conflict
    
