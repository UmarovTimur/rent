from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from src.services.order.schemas import OrderStatus


class ProductRentalCalendarSlot(BaseModel):
    slot_start: datetime
    slot_end: datetime
    effective_capacity: int
    order_reserved_quantity: int
    manual_reserved_quantity: int
    blocked_quantity: int
    available_quantity: int
    is_closed: bool
    is_available: bool


class ProductRentalCalendarResponse(BaseModel):
    product_id: int
    rental_id: int
    total_quantity: int
    slot_duration_minutes: int
    range_start: datetime
    range_end: datetime
    slots: list[ProductRentalCalendarSlot]


class RentalAvailabilityCheck(BaseModel):
    product_id: int
    quantity: int = Field(..., ge=1)
    rental_start: datetime
    rental_end: datetime

    @model_validator(mode="after")
    def validate_range(self):
        if self.rental_end <= self.rental_start:
            raise ValueError("rental_end must be later than rental_start")
        return self


class RentalOrderItemBrief(BaseModel):
    order_item_id: int
    product_id: int
    product_name: str | None = None
    quantity: int
    unit_price: int
    rental_start: datetime | None
    rental_end: datetime | None


class RentalOrderSummary(BaseModel):
    order_id: int
    telegram_id: int
    first_name: str | None
    username: str | None
    phone: str | None
    status: OrderStatus
    rental_start: datetime
    rental_end: datetime
    total_price: int
    items: list[RentalOrderItemBrief]

    class Config:
        from_attributes = True


class RentalOrderDetail(RentalOrderSummary):
    order_date: datetime
    payment_option: str
    address: str | None
    comment: str | None
    allowed_transitions: list[str]


class RentalStatusUpdate(BaseModel):
    status: OrderStatus
