from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/fintech_db"
    )
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30

    # Google Gemini
    google_api_key: str = ""
    google_model: str = "gemini-2.5-flash"

    # Redis
    redis_url: str = "redis://localhost:6379"
    cache_ttl_seconds: int = 3600

    # App
    app_name: str = "AI Fintech Platform"
    app_version: str = "0.1.0"
    log_level: str = "INFO"
    debug: bool = False

    # Market sizing defaults
    market_radius_default_m: int = 1000
    market_city_radius_m: int = 15000


settings = Settings()
