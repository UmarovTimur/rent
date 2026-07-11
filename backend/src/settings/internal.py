from pydantic_settings import BaseSettings, SettingsConfigDict


class InternalSettings(BaseSettings):
    """Shared secret for trusted server-to-server calls (backend <-> bot)."""

    api_token: str = ""

    model_config = SettingsConfigDict(env_prefix="internal_")
