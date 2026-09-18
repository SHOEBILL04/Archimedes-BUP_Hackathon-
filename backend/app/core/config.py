from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="Smart Campus Energy Optimization API", alias="APP_NAME")
    app_env: Literal["development", "staging", "production", "test"] = Field(
        default="development", alias="APP_ENV"
    )
    debug: bool = Field(default=True, alias="DEBUG")

    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")

    database_url: str = Field(
        default="sqlite:///./data/smart_campus_energy.db",
        alias="DATABASE_URL",
    )

    @property
    def resolved_database_url(self) -> str:
        """Resolve SQLite relative paths against BACKEND_DIR so it works from root or subdirectories."""
        if self.database_url.startswith("sqlite:///./"):
            rel = self.database_url.replace("sqlite:///./", "")
            abs_path = BACKEND_DIR / rel
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite:///{abs_path}"
        return self.database_url

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")

    llm_timeout_seconds: int = Field(default=8, alias="LLM_TIMEOUT_SECONDS")
    solver_timeout_seconds: int = Field(default=5, alias="SOLVER_TIMEOUT_SECONDS")
    api_timeout_seconds: int = Field(default=29, alias="API_TIMEOUT_SECONDS")

    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://frontend:3000",
    ]


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
