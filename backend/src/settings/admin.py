from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class AdminSettings(BaseSettings):
    telegram_ids: Annotated[list[int], NoDecode] = []

    model_config = SettingsConfigDict(env_prefix="admin_")

    @field_validator("telegram_ids", mode="before")
    @classmethod
    def parse_comma_separated(cls, v: object) -> object:
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v
