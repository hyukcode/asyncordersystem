from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.order import (
    OrderCreate,
    OrderResponse,
)
from app.services.order_service import OrderService

router = APIRouter(
    prefix="/orders",
    tags=["orders"],
)

@router.post(
    "",
    response_model=OrderResponse,
)
async def create_order(
    data: OrderCreate,
    session: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
):
    service = OrderService(session)
    return await service.create_order(
        user_id=data.user_id,
        amount=data.amount,
    )

@router.get(
    "/{order_id}",
    response_model=OrderResponse
)
async def get_order(
    order_id: int,
    session: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
): 
    service = OrderService(session)
    order = await service.get_order(order_id)
    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found",
        )
    return order