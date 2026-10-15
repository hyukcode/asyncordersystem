from datetime import datetime
from decimal import Decimal 

from pydantic import BaseModel, ConfigDict, Field 

from typing import Literal

class OrderStatusUpdate(BaseModel):
    status: Literal[
        "PENDING",
        "PROCESSING",
        "SUCCESS",
        "FAILED",
    ]

class OrderCreate(BaseModel):
    user_id: int = Field(gt=0)

    amount: Decimal = Field(
        gt=0,
        max_digits=10,
        decimal_places=2,
    )

class OrderResponse(BaseModel):
    id: int
    order_no: str
    user_id: int
    amount: Decimal
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )