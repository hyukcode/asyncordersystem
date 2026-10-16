import asyncio

from sqlalchemy import update

from app.core.database import AsyncSessionFactory
from app.models.order import Order
from app.repositories.order_repository import OrderRepository

async def update_order(
    name: str,
    status: str,
    delay: int,
):
    async with AsyncSessionFactory() as session:
        repo = OrderRepository(session)

        order = await repo.get_by_id(1)

        print(name, "read:", order.status, "version:", order.version)

        await asyncio.sleep(delay)

        success = await repo.update_status_optimistic(
            order=order,
            status=status,
        )

        if not success:
            await session.rollback()
            print(name, "conflict")
            return

        await session.commit()
        print(name, "success")

async def update_to_processing():
    async with AsyncSessionFactory() as session:
        repo = OrderRepository(session)

        order = await repo.get_by_id_for_update(1)

        print("A got lock:", order.status)

        await asyncio.sleep(3)

        order.status = "PROCESSING"

        await session.commit()

        print("A committed:", order.status)

async def update_to_failed():
    async with AsyncSessionFactory() as session:
        repo = OrderRepository(session)

        print("B trying to get lock")

        order = await repo.get_by_id_for_update(1)

        print("B got lock:", order.status)

        order.status = "FAILED"

        await session.commit()

        print("B commited:", order.status)

async def main():
    await asyncio.gather(
        update_order(
            "A",
            "PROCESSING",
            3,
        ),
        update_order(
            "B",
            "FAILED",
            1,
        ),
        # update_to_processing(),
        # update_to_failed(),
    )

if __name__ == "__main__":
    asyncio.run(main())