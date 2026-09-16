from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/stock_fund_predictor"
    )
    redis_url: str = Field(default="redis://localhost:6379/0")
    live_tick_retention_days: int = Field(default=30, ge=1)
    live_candle_retention_days: int = Field(default=180, ge=1)


@lru_cache

def get_settings() -> Settings:
    return Settings()
