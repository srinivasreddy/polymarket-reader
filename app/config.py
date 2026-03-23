from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    gamma_base_url: str = "https://gamma-api.polymarket.com"
    clob_base_url: str = "https://clob.polymarket.com"
    request_timeout_seconds: float = 20.0
    max_connections: int = 20
    max_keepalive_connections: int = 10

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="POLY_",
        extra="ignore",
    )


settings = Settings()