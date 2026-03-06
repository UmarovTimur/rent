from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class BasketItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(..., ge=1)
    rental_start: datetime | None = None
    rental_end: datetime | None = None

    @model_validator(mode="after")
    def validate_rental_range(self):
        if (self.rental_start is None) != (self.rental_end is None):
            raise ValueError("rental_start and rental_end must be provided together")
        if self.rental_start and self.rental_end and self.rental_end <= self.rental_start:
            raise ValueError("rental_end must be later than rental_start")
        return self


class BasketItemResponse(BaseModel):
    basket_item_id: int
    product_id: int
    quantity: int
    rental_start: datetime | None = None
    rental_end: datetime | None = None


class BasketResponse(BaseModel):
    basket_id: int
    user_id: int
    discount: float | None
    items: list[BasketItemResponse]
    total_price: int


class QuantityUpdate(BaseModel):
    basket_item_id: int
    quantity: int
