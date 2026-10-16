from decimal import Decimal

import pytest
from pydantic import ValidationError
from app.schemas.order import OrderCreate, OrderStatusUpdate

def test_order_create_success():
    order = OrderCreate(
        user_id=1001,
        amount=Decimal("100.00"),
    )
    assert order.model_dump() == {
        "user_id": 1001,
        "amount": Decimal("100.00"),
    }

def test_order_create_reject_zero_amount():
    with pytest.raises(ValidationError):
        OrderCreate(
            user_id=1001,
            amount=Decimal("0.00"),
        )

@pytest.mark.parametrize(
    "amount",
    [
        "0",
        "-1.00",
        "-100.00",
    ],
)
def test_order_create_rejects_non_positive_amount(
    amount: str,
):
    with pytest.raises(ValidationError):
        OrderCreate(
            user_id=1001,
            amount=amount,
        )

def test_order_status_success():
    data = OrderStatusUpdate(status="SUCCESS")
    assert data.status == "SUCCESS"

def test_order_status_invalid():
    with pytest.raises(ValidationError):
        OrderStatusUpdate(status="ABC")
