import json
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from src.services.category.schemas import CategoryResponse


class ProductCreate(BaseModel):
    name: str = Field(..., max_length=30)
    description: str
    category_id: int
    price: int = Field(..., ge=0)
    is_addon: bool = False
    price_mode: str = "per_day"

    @model_validator(mode="before")
    @classmethod
    def to_py_dict(cls, data: Any) -> dict[str, Any]:
        return json.loads(data)


class AddonResponse(BaseModel):
    """Lightweight add-on view offered on a parent product."""

    product_id: int
    name: str
    price: int
    price_mode: str
    image_url: str | None = None
    # 0 = optional add-on; >0 = kit component pre-included with this quantity.
    default_quantity: int = 0

    class Config:
        from_attributes = True


class ProductResponse(BaseModel):
    product_id: int
    name: str
    description: str
    price: int
    # Catalog display price: `price` plus the price of any pre-included kit
    # components (default_quantity > 0 links). Equals `price` for a normal
    # product with only optional add-ons. Use this for catalog listings;
    # use `price` (the raw parent price) for basket/order billing.
    display_price: int = 0
    image_url: str | None
    image_urls: list[str] = []
    is_addon: bool = False
    price_mode: str = "per_day"
    category: CategoryResponse

    class Config:
        from_attributes = True

    @field_validator("image_urls", mode="before")
    @classmethod
    def null_to_list(cls, v: object) -> list:
        return v if isinstance(v, list) else []


class ProductUpdate(BaseModel):
    name: str = Field(None)
    description: str = Field(None)
    category_id: int = Field(None)
    price: int = Field(None, ge=0)
    is_addon: bool = Field(None)
    price_mode: str = Field(None)

    @model_validator(mode="before")
    @classmethod
    def to_py_dict(cls, data: Any) -> dict[str, Any]:
        return json.loads(data)
