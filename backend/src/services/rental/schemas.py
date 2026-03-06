from datetime import datetime

from pydantic import BaseModel, Field, model_validator


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
