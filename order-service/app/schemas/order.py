from datetime import datetime
from decimal import Decimal 

from pydantic import BaseModel, ConfigDict, Field 

class OrderCreate(BaseModel):
    user_id: int

    amount: Decimal = Field(
        gt=0,
        decimal_places=2,
    )

class OrderResponse(BaseModel):
    id: int
    order_no: str
    user_id: int
    amount: Decimal
    status: str
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )