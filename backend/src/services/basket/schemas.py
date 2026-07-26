from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class AddonSelection(BaseModel):
    product_id: int
    quantity: int = Field(1, ge=1, le=99)


class BasketItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(..., ge=1, le=99)
    rental_start: datetime | None = None
    rental_end: datetime | None = None
    # Selected add-ons (each with its own quantity) attached as child items.
    addons: list[AddonSelection] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_rental_range(self):
        if (self.rental_start is None) != (self.rental_end is None):
            raise ValueError("rental_start and rental_end must be provided together")
        if self.rental_start and self.rental_end and self.rental_end <= self.rental_start:
            raise ValueError("rental_end must be later than rental_start")
        return self


class BasketItemAddonResponse(BaseModel):
    basket_item_id: int
    product_id: int
    name: str
    price: int
    price_mode: str
    quantity: int


class BasketItemResponse(BaseModel):
    basket_item_id: int
    product_id: int
    quantity: int
    rental_start: datetime | None = None
    rental_end: datetime | None = None
    addons: list[BasketItemAddonResponse] = Field(default_factory=list)


class BasketDatesUpdate(BaseModel):
    """Basket-level trip window; both dates required together."""

    rental_start: datetime
    rental_end: datetime

    @model_validator(mode="after")
    def validate_rental_range(self):
        if self.rental_end <= self.rental_start:
            raise ValueError("rental_end must be later than rental_start")
        return self


class BasketResponse(BaseModel):
    basket_id: int
    user_id: int
    discount: float | None
    rental_start: datetime | None = None
    rental_end: datetime | None = None
    items: list[BasketItemResponse]
    total_price: int


class QuantityUpdate(BaseModel):
    basket_item_id: int
    quantity: int = Field(..., ge=1, le=99)
