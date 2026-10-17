from decimal import Decimal
from typing import Literal 

from pydantic import BaseModel

class OrderCreatedPayload(BaseModel):
    order_id: int
    order_no: str
    user_id: int
    amount: Decimal
    status: str

# JSON -> Pydantic -> OrderCreatedEvent
class OrderCreatedEvent(BaseModel):
    event_id: str
    event_type: Literal["order.created"]
    payload: OrderCreatedPayload