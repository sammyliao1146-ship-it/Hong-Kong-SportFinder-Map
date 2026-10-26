import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class Settings:
    api_key: str = field(repr=False)
    model: str
    base_url: str
    cors_origins: list[str]
    agent_tool_transport: str = "function"
    redis_url: str = "redis://127.0.0.1:6379/0"
    cache_prefix: str = "hksf"
    chat_rate_limit: int = 20
    chat_rate_window_seconds: int = 60


@lru_cache
def get_settings() -> Settings:
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    return Settings(
        agent_tool_transport=os.getenv("AGENT_TOOL_TRANSPORT", "function"),
        api_key=os.getenv("BAI_API_KEY", ""),
        model=os.getenv("BAI_MODEL", "gpt-6.1-sol"),
        base_url=os.getenv("BAI_BASE_URL", "https://api.b.ai/v1"),
        cors_origins=[origin.strip() for origin in os.getenv(
            "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",") if origin.strip()],
        redis_url=os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"),
        cache_prefix=os.getenv("CACHE_PREFIX", "hksf"),
        chat_rate_limit=int(os.getenv("CHAT_RATE_LIMIT", "20")),
        chat_rate_window_seconds=int(os.getenv("CHAT_RATE_WINDOW_SECONDS", "60")),
    )
