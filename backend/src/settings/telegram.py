from pydantic_settings import BaseSettings, SettingsConfigDict


class TelegramSettings(BaseSettings):
    token: str = ""

    model_config = SettingsConfigDict(env_prefix="bot_")
