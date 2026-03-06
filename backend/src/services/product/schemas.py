import json
from typing import Any

from pydantic import BaseModel, Field, model_validator

from src.services.category.schemas import CategoryResponse


class ProductCreate(BaseModel):
    name: str = Field(..., max_length=30)
    description: str
    category_id: int
    price: int = Field(..., ge=0)

    @model_validator(mode="before")
    @classmethod
    def to_py_dict(cls, data: Any) -> dict[str, Any]:
        return json.loads(data)


class ProductResponse(BaseModel):
    product_id: int
    name: str
    description: str
    price: int
    image_url: str | None
    category: CategoryResponse

    class Config:
        from_attributes = True


class ProductUpdate(BaseModel):
    name: str = Field(None)
    description: str = Field(None)
    category_id: int = Field(None)
    price: int = Field(None, ge=0)

    @model_validator(mode="before")
    @classmethod
    def to_py_dict(cls, data: Any) -> dict[str, Any]:
        return json.loads(data)
