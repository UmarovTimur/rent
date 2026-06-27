from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthSettings(BaseSettings):
    secret: str = "dev-secret-change-in-production"
    algorithm: str = "HS256"
    expire_days: int = 30

    model_config = SettingsConfigDict(env_prefix="jwt_")
