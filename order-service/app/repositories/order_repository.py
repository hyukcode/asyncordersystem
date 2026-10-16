from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order

# repository支持for update 并发更新问题 Lost Update  -> MySQL悲观锁

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

    async def get_by_id_for_update(
        self,
        order_id: int,
    ) -> Order | None:
    # with_for_update() 生成类似 select * from orders where id = 1 for update;
    # for update 对查询到的记录加排他锁
        stmt = select(Order).where(Order.id == order_id).with_for_update()
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

    async def update_status_optimistic(
        self,
        order: Order,
        status: str,
    ) -> bool:
        current_version = order.version
        # Order.version == current_version 乐观锁的灵魂，携带旧版本
        stmt = (
            update(Order)
            .where(
                Order.id == order.id, 
                Order.version == current_version,
            )
            .values(
                status=status,
                version=current_version+1,
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount == 1

        # Compare And Set, CAS
        # UPDATE orders
        # SET 
        #     status = 'PROCESSING',
        #     version = 2
        # WHERE 
        #     id = 1
        #     AND version = 1;
