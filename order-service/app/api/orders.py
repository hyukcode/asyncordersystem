from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.order import (
    OrderCreate,
    OrderResponse,
    OrderStatusUpdate,
)
from app.services.order_service import OrderService

from app.core.exceptions import (
    InvalidOrderStatusTransitionError,
    OptimisticLockError,
    OrderNotFoundError,
)

router = APIRouter(
    prefix="/orders",
    tags=["orders"],
)

@router.post(
    "",
    response_model=OrderResponse,
    status_code=201,
)
async def create_order(
    data: OrderCreate,
    session: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
    idempotency_key: Annotated[
        str,
        Header(alias="Idempotency-Key"),
    ],
):
    service = OrderService(session)
    order, created = await service.create_order(
        data,
        idempotency_key,
    )
    if not created:
        response.status_code = 200
    return order

@router.get(
    "/{order_id}",
    response_model=OrderResponse,
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

@router.put(
    "/{order_id}/status",
    response_model=OrderResponse,
)
async def update_order_status(
    order_id: int,
    data: OrderStatusUpdate,
    session: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
):
    service = OrderService(session)

    try:
        return await service.update_order_status(
            order_id=order_id,
            data=data,
        )

    except OrderNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )
    
    except InvalidOrderStatusTransitionError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        )

    except OptimisticLockError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        )
