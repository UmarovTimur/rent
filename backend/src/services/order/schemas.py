from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class OrderStatus(StrEnum):
    CREATED = "created"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    TAKEN = "taken"
    CANCELED = "canceled"


class PaymentOption(StrEnum):
    CARD = "card"
    CASH = "cash"


class OrderCreate(BaseModel):
    basket_id: int
    payment_option: PaymentOption = PaymentOption.CARD
    comment: str | None = None
    status: OrderStatus = OrderStatus.CREATED
    first_name: str | None
    address: str | None
    phone: str | None
    discount: float | None

    class Config:
        use_enum_values = True

class OrderItemResponse(BaseModel):
    order_item_id: int
    product_id: int
    unit_price: int
    quantity: int
    rental_start: datetime | None = None
    rental_end: datetime | None = None


class OrderResponse(BaseModel):
    order_id: int
    basket_id: int
    order_date: datetime
    payment_option: str
    total_price: int
    comment: str | None
    status: str
    first_name: str | None
    address: str | None
    phone: str | None
    discount: float | None
    items: list[OrderItemResponse]

    class Config:
        from_attributes = True
