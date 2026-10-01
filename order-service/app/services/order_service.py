import uuid
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.repositories.order_repository import OrderRepository

class OrderService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = OrderRepository(session)

    async def create_order(
        self,
        user_id: int,
        amount: Decimal,
    ) -> Order:
        order_no = f"ORD={uuid.uuid4().hex[:16]}"
        order = Order(
            order_no=order_no,
            user_id=user_id,
            amount=amount,
            status="PENDING",
        )
        try:
            order = await self.repository.create(order)
            await self.session.commit()
            return order
        except Exception:
            await self.session.rollback()
            raise
        
    async def get_order(
        self,
        order_id: int,
    ) -> Order | None:
        return await self.repository.get_by_id(
            order_id
        )