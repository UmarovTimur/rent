from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


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
    # Client-supplied order fields. Deliberately NO `status`/`discount` here:
    # the server always creates orders as CREATED and never trusts a
    # client-provided status or discount (a client setting status="taken" would
    # otherwise skip payment/approval and hold inventory for free). basket_id is
    # also ignored server-side in favour of the caller's own basket.
    basket_id: int
    payment_option: PaymentOption = PaymentOption.CARD
    comment: str | None = Field(default=None, max_length=1000)
    first_name: str | None = Field(default=None, max_length=100)
    address: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=100)
    # Redeem the user's bonus balance as a discount on this order. The server
    # computes the actual amount (capped at the user's own balance and the
    # order total) — the client only toggles yes/no, never supplies a number.
    use_coins: bool = False

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
    username: str | None = None  # the client's Telegram @username, for admin contact
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
