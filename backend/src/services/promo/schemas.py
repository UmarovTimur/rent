from pydantic import BaseModel, Field


class PromoResponse(BaseModel):
    promo_id: int
    title: str | None = None
    # Ordered media filenames (cover first). The client prefixes /media/promos/.
    frames: list[str] = Field(default_factory=list)
