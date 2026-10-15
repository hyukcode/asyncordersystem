import uuid
import hashlib
import json

from fastapi import HTTPException

from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.core.redis_lock import RedisLock
from app.repositories.order_repository import OrderRepository
from app.schemas.order import OrderCreate, OrderStatusUpdate

from redis.asyncio import Redis

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
        redis: Redis | None = None,
    ):
        self.session = session
        self.redis = redis
        self.repository = OrderRepository(session)

    def format_amount(amount: Decimal) -> str:
        return str(amount.quantize(Decimal("0.01")))

    @staticmethod
    def request_hash(data: OrderCreate) -> str:

        payload = {
            "user_id": data.user_id,
            "amount": format_amount(data.amount),
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
        idempotency_key: str,
    ) -> Order:

        if self.redis is None:
            raise RuntimeError("Redis is not configured")
        
        fingerprint = self.request_hash(data)

        lock_name = (
            "order:lock:"
            + hashlib.sha256(
                idempotency_key.encode()
            ).hexdigest()
        )

        lock = RedisLock(
            self.redis,
            key=lock_name,
            ttl=30,
        )

        acquired = await lock.acquire()

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
                await self.repository.create(order)
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
            return order, True
        
        finally:
            await lock.release()
        
    async def get_order(
        self,
        order_id: int,
    ) -> Order | None:
        return await self.repository.get_by_id(
            order_id
        )

    async def update_order_status(
        self,
        order_id: int,
        data: OrderStatusUpdate,
    ) -> Order | None:
        order = await self.repository.get_by_id(order_id)
        if order is None:
            return None

        allowed_statuses = STATUS_TRANSITIONS.get(
            order.status,
            set(),
        )

        if data.status not in allowed_statuses:
            raise ValueError(
                f"invalid status transition:"
                f"{order.status} -> {data.status}"
            )

        try:
            order = await self.repository.update_status(
                order=order,
                status=data.status,
            )
            await self.session.commit()
            return order
        except Exception:
            await self.session.rollback()
            raise
    
