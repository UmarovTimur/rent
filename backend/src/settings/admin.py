from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class AdminSettings(BaseSettings):
    telegram_ids: Annotated[list[int], NoDecode] = []

    # Signing key for the admin session cookie shared by the SQLAdmin panel and
    # the rental calendar API. Must be set and kept secret in production.
    session_secret: str = "change-me-in-production"
    # Mark the session cookie Secure (HTTPS only). Enable in production.
    session_https_only: bool = False

    # Credentials used to seed the first admin when the admin_users table is empty.
    bootstrap_username: str = ""
    bootstrap_password: str = ""

    model_config = SettingsConfigDict(env_prefix="admin_")

    @field_validator("telegram_ids", mode="before")
    @classmethod
    def parse_comma_separated(cls, v: object) -> object:
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v
