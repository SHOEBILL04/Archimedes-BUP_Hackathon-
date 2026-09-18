from functools import lru_cache
import os

from pydantic import BaseModel, Field


class Settings(BaseModel):
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    llm_timeout_seconds: float = Field(default=8.0, gt=0)
    solver_timeout_seconds: float = Field(default=5.0, gt=0)
    api_timeout_seconds: float = Field(default=29.0, gt=0)
    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1, le=65535)


@lru_cache
def get_settings() -> Settings:
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        llm_timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "8")),
        solver_timeout_seconds=float(os.getenv("SOLVER_TIMEOUT_SECONDS", "5")),
        api_timeout_seconds=float(os.getenv("API_TIMEOUT_SECONDS", "29")),
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
    )
