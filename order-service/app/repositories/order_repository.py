from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order

class OrderRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, order: Order) -> Order:
        # Transient -> Pending
        self.session.add(order)
        await self.session.flush()
        # 从数据库中读回数据
        await self.session.refresh(order)
        return order
    
    async def get_by_id(self, order_id: int) -> Order | None:
        stmt =  select(Order).where(
            Order.id == order_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_order_no(
        self, order_no: str
    ) -> Order | None:
        stmt = select(Order).where(
            Order.order_no == order_no
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_idempotency_key(
        self,
        key: str,
    ) -> Order | None:
        stmt = select(Order).where(
            Order.idempotency_key == key
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_status(
        self,
        order: Order,
        status: str,
    ) -> Order:
    # persistent -> dirty
        order.status = status
        await self.session.flush()
        await self.session.refresh(order)
        return order
