"""Runtime configuration helpers."""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import List

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = BASE_DIR / ".env"
load_dotenv(ENV_PATH, override=False)


def _csv_env(name: str) -> List[str]:
    raw = os.getenv(name, "")
    return [part.strip() for part in raw.split(",") if part.strip()]


@dataclass
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data/ct_scraper.db")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    timezone: str = os.getenv("TIMEZONE", "America/New_York")
    email_from: str = os.getenv("EMAIL_FROM", "leads@example.com")
    email_provider: str = os.getenv("EMAIL_PROVIDER", "ses")
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    stripe_api_key: str = os.getenv("STRIPE_API_KEY", "")
    stripe_webhook_secret: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    allowed_towns: List[str] | None = None

    def __post_init__(self) -> None:
        self.allowed_towns = _csv_env("ALLOWED_TOWNS") or []


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
