from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order

class OrderRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, order: Order) -> Order:
        self.session.add(order)
        await self.session.flush()
        await self.session.refresh(order)
        return order
    
    async def get_by_id(self, order_id: int) -> Order | None:
        stmt =  select(Order).where(
            Order.id == order_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()