from datetime import datetime

from sqlalchemy import Boolean, Integer, String, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from src.clients.database.base import Base


class Promo(Base):
    """A story-style promo shown as a tappable circle in the app header.

    Media is modelled exactly like Product photos (cover = image_url, remaining
    story frames = image_urls) so it reuses the admin multi-photo widget. Video is
    a planned addition (a separate media list); for now a promo is a set of photos.
    """

    __tablename__ = "promos"
    __table_args__ = {"extend_existing": True}

    promo_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(60), nullable=True)
    # Cover / first story frame.
    image_url: Mapped[str] = mapped_column(nullable=True)
    # Remaining story frames, in order.
    image_urls: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=True, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Admin multi-photo widget compatibility (mirrors Product): the form has a
    # virtual "upload_images" field and reads "existing_photos" on edit.
    upload_images = None

    @property
    def existing_photos(self) -> list[str]:
        """All current frame filenames (cover first). Not a DB column."""
        return ([self.image_url] if self.image_url else []) + list(self.image_urls or [])

    @existing_photos.setter
    def existing_photos(self, _value) -> None:
        # Writes are handled in PromoAdmin.after_model_change; ignore direct assignment.
        pass

    def __str__(self) -> str:
        return self.title or f"Promo #{self.promo_id}"

    __repr__ = __str__
