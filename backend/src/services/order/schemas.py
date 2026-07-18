from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class OrderStatus(StrEnum):
    CREATED = "created"
    IN_PROGRESS = "in_progress"
    TAKEN = "taken"          # handed over to the client ("Отдал") — admin marker, gates RETURNED
    RETURNED = "returned"    # client gave the gear back — successful outcome, releases the slot
    COMPLETED = "completed"  # closed without a successful return (no-show, dispute, etc.) — unsuccessful outcome
    CANCELED = "canceled"
    PAUSED = "paused"


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
    product_name: str | None = None
    unit_price: int
    quantity: int
    rental_start: datetime | None = None
    rental_end: datetime | None = None
    # Set on add-on lines → the order_item_id of their parent product line.
    parent_order_item_id: int | None = None


class OrderResponse(BaseModel):
    order_id: int
    user_id: int
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
